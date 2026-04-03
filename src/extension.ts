import * as cp from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

const OUTPUT_CHANNEL = vscode.window.createOutputChannel('BibCheck');

type UpdateMode = 'conservative' | 'force';
type OutputMode = 'overwrite' | 'copy';

interface RunOptions {
  rewriteKeys: boolean;
  updateMode: UpdateMode;
  outputMode: OutputMode;
  syncTex: boolean;
}

export function activate(context: vscode.ExtensionContext): void {
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  status.text = 'BibCheck';
  status.tooltip = 'Scan the workspace for BibTeX issues';
  status.command = 'bibtexRefiner.refineWorkspaceBibtex';
  status.show();

  context.subscriptions.push(status, OUTPUT_CHANNEL);

  context.subscriptions.push(
    vscode.commands.registerCommand('bibtexRefiner.refineBibtex', async () => {
      const picked = await pickBibFile();
      if (!picked) {
        return;
      }
      await runSingleFileRefiner(context, picked);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('bibtexRefiner.refineActiveBibtex', async (resource?: vscode.Uri) => {
      const target = await resolveSingleBibTarget(resource);
      if (!target) {
        return;
      }
      await runSingleFileRefiner(context, target);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('bibtexRefiner.refineWorkspaceBibtex', async () => {
      const bibFiles = await collectWorkspaceBibFiles();
      if (bibFiles.length === 0) {
        vscode.window.showInformationMessage('No .bib files were found in the workspace.');
        return;
      }
      await runBatchRefiner(context, bibFiles, 'workspace');
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('bibtexRefiner.refineFolderBibtex', async (resource?: vscode.Uri) => {
      const folder = await resolveFolderTarget(resource);
      if (!folder) {
        return;
      }
      const bibFiles = await collectBibFilesInFolder(folder);
      if (bibFiles.length === 0) {
        vscode.window.showInformationMessage('No .bib files were found in the selected folder.');
        return;
      }
      await runBatchRefiner(context, bibFiles, folder.fsPath);
    })
  );
}

async function pickBibFile(): Promise<string | undefined> {
  const picked = await vscode.window.showOpenDialog({
    title: 'Select BibTeX file',
    canSelectMany: false,
    canSelectFolders: false,
    canSelectFiles: true,
    filters: { BibTeX: ['bib'] },
  });
  return picked?.[0]?.fsPath;
}

async function resolveSingleBibTarget(resource?: vscode.Uri): Promise<string | undefined> {
  if (resource && resource.fsPath.toLowerCase().endsWith('.bib')) {
    return resource.fsPath;
  }

  const editor = vscode.window.activeTextEditor;
  const activeUri = editor?.document.uri;
  if (activeUri && activeUri.fsPath.toLowerCase().endsWith('.bib')) {
    return activeUri.fsPath;
  }

  return pickBibFile();
}

async function resolveFolderTarget(resource?: vscode.Uri): Promise<vscode.Uri | undefined> {
  if (resource && !resource.fsPath.toLowerCase().endsWith('.bib')) {
    return resource;
  }

  const picked = await vscode.window.showOpenDialog({
    title: 'Select folder to scan for BibTeX files',
    canSelectMany: false,
    canSelectFolders: true,
    canSelectFiles: false,
  });
  return picked?.[0];
}

async function collectWorkspaceBibFiles(): Promise<string[]> {
  const folders = vscode.workspace.workspaceFolders ?? [];
  const files = await Promise.all(folders.map((folder) => collectBibFilesInFolder(folder.uri)));
  return [...new Set(files.flat())].sort();
}

async function collectBibFilesInFolder(folder: vscode.Uri): Promise<string[]> {
  const patterns = await vscode.workspace.findFiles(new vscode.RelativePattern(folder, '**/*.bib'));
  return patterns.map((uri) => uri.fsPath).sort();
}

async function runSingleFileRefiner(context: vscode.ExtensionContext, inputPath: string): Promise<void> {
  const options = await promptRunOptions({ batch: false });
  if (!options) {
    return;
  }
  await runRefiner(context, inputPath, options);
}

async function runBatchRefiner(context: vscode.ExtensionContext, inputPaths: string[], sourceLabel: string): Promise<void> {
  const options = await promptRunOptions({ batch: true });
  if (!options) {
    return;
  }

  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: `BibCheck: scanning ${sourceLabel}`, cancellable: false },
    async () => {
      for (const inputPath of inputPaths) {
        await runRefiner(context, inputPath, options);
      }
    }
  );
}

async function promptRunOptions(params: { batch: boolean }): Promise<RunOptions | undefined> {
  const rewriteKeys = await vscode.window.showQuickPick(
    [
      { label: 'Preserve original cite keys', value: false },
      { label: 'Rewrite cite keys', value: true },
    ],
    { placeHolder: 'Choose how citation keys should be handled' }
  );
  if (!rewriteKeys) {
    return undefined;
  }

  const updateMode = await vscode.window.showQuickPick(
    [
      { label: 'Conservative update', value: 'conservative' as const },
      { label: 'Force canonical fields', value: 'force' as const },
    ],
    { placeHolder: 'Choose update mode' }
  );
  if (!updateMode) {
    return undefined;
  }

  const outputMode = params.batch
    ? await vscode.window.showQuickPick(
        [
          { label: 'Overwrite original .bib files', value: 'overwrite' as const },
          { label: 'Write .refined.bib copies next to originals', value: 'copy' as const },
        ],
        { placeHolder: 'Choose how batch output should be written' }
      )
    : await vscode.window.showQuickPick(
        [
          { label: 'Overwrite the input file', value: 'overwrite' as const },
          { label: 'Write a .refined.bib copy', value: 'copy' as const },
        ],
        { placeHolder: 'Choose how output should be written' }
      );
  if (!outputMode) {
    return undefined;
  }

  let syncTex = false;
  if (rewriteKeys.value) {
    const syncChoice = await vscode.window.showQuickPick(
      [
        { label: 'Do not update .tex files', value: false },
        { label: 'Update matching .tex files', value: true },
      ],
      { placeHolder: 'If keys are rewritten, should matching .tex files also be updated?' }
    );
    if (!syncChoice) {
      return undefined;
    }
    syncTex = syncChoice.value;
  }

  return {
    rewriteKeys: rewriteKeys.value,
    updateMode: updateMode.value,
    outputMode: outputMode.value,
    syncTex,
  };
}

async function runRefiner(context: vscode.ExtensionContext, inputPath: string, options: RunOptions): Promise<void> {
  const pythonPath = vscode.workspace.getConfiguration('bibtexRefiner').get<string>('pythonPath', 'python');
  const bundledScriptSetting = vscode.workspace.getConfiguration('bibtexRefiner').get<string>('scriptPath', '');
  const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(inputPath));
  const workspaceScript = workspaceFolder ? path.join(workspaceFolder.uri.fsPath, 'bibtex_refiner.py') : '';
  const bundledScript = path.join(context.extensionPath, 'bibtex_refiner.py');
  const scriptPath = bundledScriptSetting && bundledScriptSetting.trim().length > 0
    ? bundledScriptSetting
    : (fs.existsSync(workspaceScript) ? workspaceScript : bundledScript);

  if (!fs.existsSync(scriptPath)) {
    vscode.window.showErrorMessage(`Cannot find bibtex_refiner.py at: ${scriptPath}`);
    return;
  }

  const outputPath = options.outputMode === 'copy'
    ? path.join(path.dirname(inputPath), `${path.basename(inputPath, '.bib')}.refined.bib`)
    : inputPath;
  const reportPath = `${outputPath}.report.json`;
  const args = [
    scriptPath,
    inputPath,
    '-o',
    outputPath,
  ];
  if (options.rewriteKeys) {
    args.push('--rewrite-keys');
  }
  if (options.updateMode === 'force') {
    args.push('--force');
  }
  args.push('--report', reportPath);

  OUTPUT_CHANNEL.clear();
  OUTPUT_CHANNEL.appendLine(`Running: ${pythonPath} ${args.map(quoteArg).join(' ')}`);
  OUTPUT_CHANNEL.show(true);

  await new Promise<void>((resolve) => {
    const child = cp.spawn(pythonPath, args, { cwd: path.dirname(inputPath), shell: false });
    child.stdout.on('data', (chunk) => OUTPUT_CHANNEL.append(chunk.toString()));
    child.stderr.on('data', (chunk) => OUTPUT_CHANNEL.append(chunk.toString()));
    child.on('error', (err) => {
      OUTPUT_CHANNEL.appendLine(String(err));
      vscode.window.showErrorMessage(`BibCheck failed: ${err.message}`);
      resolve();
    });
    child.on('close', (code) => {
      if (code === 0) {
        vscode.window.showInformationMessage(`BibCheck finished. Output: ${outputPath}`);
        if (options.rewriteKeys && options.syncTex) {
          void syncTexFilesFromReport(reportPath, inputPath);
        }
      } else {
        vscode.window.showErrorMessage(`BibCheck exited with code ${code ?? 'unknown'}`);
      }
      resolve();
    });
  });
}

async function syncTexFilesFromReport(reportPath: string, bibPath: string): Promise<void> {
  if (!fs.existsSync(reportPath)) {
    return;
  }

  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8')) as {
    entries?: Array<{ id?: string; resolved_id?: string; changed?: boolean }>;
  };
  const mapping = new Map<string, string>();
  for (const entry of report.entries ?? []) {
    if (entry.id && entry.resolved_id && entry.id !== entry.resolved_id) {
      mapping.set(entry.id, entry.resolved_id);
    }
  }

  if (mapping.size === 0) {
    vscode.window.showInformationMessage('No citation key changes were found to apply.');
    return;
  }

  const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(bibPath));
  const root = workspaceFolder?.uri ?? vscode.Uri.file(path.dirname(bibPath));
  const texFiles = await vscode.workspace.findFiles(new vscode.RelativePattern(root, '**/*.tex'));
  let updatedFiles = 0;

  for (const texFile of texFiles) {
    const data = await vscode.workspace.fs.readFile(texFile);
    const original = Buffer.from(data).toString('utf8');
    const updated = rewriteCitationKeysInText(original, mapping);
    if (updated !== original) {
      await vscode.workspace.fs.writeFile(texFile, Buffer.from(updated, 'utf8'));
      updatedFiles += 1;
    }
  }

  vscode.window.showInformationMessage(`Updated citation keys in ${updatedFiles} .tex file(s).`);
}

function rewriteCitationKeysInText(text: string, mapping: Map<string, string>): string {
  return text.replace(/\\(cite\w*|nocite)(?:\[[^\]]*\]){0,2}\{([^{}]*)\}/g, (fullMatch, command: string, keys: string) => {
    const rewritten = keys
      .split(',')
      .map((key) => key.trim())
      .map((key) => mapping.get(key) ?? key)
      .join(', ');
    return fullMatch.replace(keys, rewritten);
  });
}

function quoteArg(value: string): string {
  if (/[\s"]/g.test(value)) {
    return `"${value.replace(/"/g, '\\"')}"`;
  }
  return value;
}

export function deactivate(): void {
  // Nothing to clean up.
}
