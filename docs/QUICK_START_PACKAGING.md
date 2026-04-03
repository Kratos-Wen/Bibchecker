# 快速打包指南 (Quick Packaging Guide)

## 🚀 快速开始 - 5分钟打包

### 前提条件
```bash
# 检查 Node.js 版本
node --version  # 需要 v16+

# 检查 npm
npm --version
```

### 第1步：安装依赖
```bash
cd F:\Hackathon\Google_Scholar_Check

# 安装 Node 包
npm install

# 全局安装打包工具
npm install -g vsce
```

### 第2步：编译 TypeScript
```bash
# 编译 src/extension.ts → dist/extension.js
npm run compile

# 验证输出
dir dist\
# 应该包含: extension.js, extension.d.ts, extension.js.map
```

### 第3步：本地打包 (生成 .vsix 文件)
```bash
# 创建可分发的扩展包
vsce package

# 输出文件: bibcheck-0.1.0.vsix (约 5-10 MB)
```

---

## 📦 分发方式

### 方式 A: 本地分发 (无需账户)
```bash
# 用户可以直接安装 .vsix 文件:
code --install-extension bibcheck-0.1.0.vsix
```

### 方式 B: VS Code 官方市场 (需要账户)

#### 步骤 1: 创建开发者账户
1. 访问: https://marketplace.visualstudio.com/manage
2. 用 Microsoft 账户登录 (没有的话,创建一个免费账户)
3. 创建发布者记录 (Publisher)

#### 步骤 2: 获取个人访问令牌 (PAT)
1. 访问: https://dev.azure.com
2. 用户设置 → 个人访问令牌
3. 新建令牌:
   - 名称: `vsce-publishing`
   - 作用域: `Marketplace > Manage`
   - 过期时间: 1 年
4. 复制并保存此令牌 (重要!)

#### 步骤 3: 更新 package.json
```json
{
  "publisher": "your-publisher-name",  // 改为你的发布者名称
  "repository": {
    "type": "git",
    "url": "https://github.com/your-username/bibcheck"
  },
  ...
}
```

#### 步骤 4: 登录并发布
```bash
# 登录 (首次)
vsce login your-publisher-name
# 粘贴你的 PAT 令牌

# 发布到市场
vsce publish

# 你的扩展将在这里可用:
# https://marketplace.visualstudio.com/items?itemName=your-publisher.bibcheck
```

---

## 🔄 更新已发布的扩展

```bash
# 1. 更新 package.json 中的版本
# 改: "version": "0.1.0" → "0.1.1"

# 2. 编译
npm run compile

# 3. 发布更新
vsce publish

# VS Code 用户会自动收到更新通知
```

---

## ✅ 发布前检查表

- [ ] Node.js v16+ 已安装 (`node --version`)
- [ ] npm 依赖已安装 (`npm install` 完成)
- [ ] VSCE 全局工具已安装 (`npm install -g vsce`)
- [ ] TypeScript 编译成功 (`npm run compile`)
- [ ] dist/extension.js 存在且大小 > 0
- [ ] .vscodeignore 文件已创建
- [ ] package.json 中的发布者名称已更新 ✅ 完成!
- [ ] LICENSE 文件已创建 ✅ 完成!
- [ ] CHANGELOG.md 已创建 ✅ 完成!
- [ ] README.md 内容清晰明确
- [ ] 本地测试成功: `code --install-extension bibcheck-0.1.0.vsix`

---

## 📋 文件清单

发布所需的文件 (✅ = 已准备):

```
✅ package.json         - 扩展配置 (已更新发布字段)
✅ src/extension.ts     - 扩展源代码
✅ dist/extension.js    - 编译后的代码
✅ README.md            - 功能说明
✅ LICENSE              - MIT 许可证
✅ CHANGELOG.md         - 更新日志
✅ .vscodeignore        - 打包排除规则
✅ requirements.txt     - Python 依赖
✅ bibtex_refiner.py    - Python 主程序
✅ BIBTEX_VALIDATOR_DOCUMENTATION_EN.md - 4个特性文档
```

---

## 🐛 常见问题

### Q: 编译失败 "Cannot find module 'vscode'"
```bash
npm install
npm install --save-dev @types/vscode
npm run compile
```

### Q: vsce 命令未找到
```bash
npm install -g vsce
# 或
npx vsce package
```

### Q: 打包失败 "main entry point is missing"
```bash
# 确保 dist/extension.js 存在
npm run compile
ls dist/extension.js
```

### Q: 发布失败 "publisher not recognized"
```bash
# 更新 package.json 中的发布者名称
# "publisher": "your-actual-publisher-name"
vsce login your-actual-publisher-name
```

### Q: 如何在 VS Code 中测试?
```bash
# 调试模式
F5  # 或 Code > Run > Start Debugging

# 或直接安装本地 .vsix
code --install-extension bibcheck-0.1.0.vsix
```

---

## 📚 更多资源

- **完整指南**: 查看 `VSCODE_EXTENSION_GUIDE.md`
- **VS Code API**: https://code.visualstudio.com/api
- **VSCE 文档**: https://www.npmjs.com/package/vsce
- **发布指南**: https://code.visualstudio.com/api/working-with-extensions/publishing-extension
- **VS Code 市场**: https://marketplace.visualstudio.com/

---

## 💡 提示

### 开发模式
```bash
# Watch 模式 - 自动重新编译
npm run watch
```

### 生成 .vsix 文件
```bash
# 不发布, 只生成离线包
vsce package
vsce package --out my-custom-name.vsix
```

### 验证前
```bash
# 验证必要字段
vsce show
```

---

**下一步**: 按照上面的步骤 1-3 快速打包你的第一个 .vsix 文件! 🎉

如有问题,请参考 `VSCODE_EXTENSION_GUIDE.md` 中的完整指南。
