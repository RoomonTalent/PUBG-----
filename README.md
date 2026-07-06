<!--
 * @Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
 * @Date: 2026-07-05 21:55:12
 * @LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
 * @LastEditTime: 2026-07-05 22:45:30
 * @FilePath: \PUBG迫击炮测距\README.md
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
# PUBG 迫击炮测距工具 (PUBG Mortar Ranging Tool)

一个为 PUBG 游戏设计的迫击炮测距辅助工具。通过透明覆盖层在游戏地图上标记两点并计算像素距离，结合参考标定值实时换算实际距离（米）。

## 功能

- **自动检测 PUBG 启动** — 支持后台轮询检测 `TslGame.exe` 进程，游戏启动后自动激活覆盖层
- **F8 快捷菜单** — 呼出参考值输入框，可拖动位置，位置自动记忆
- **测距标记** — 右键或中键任意组合标记两个点，自动绘制连线并在中点显示像素距离和实际距离（米）
- **中键标定** — 中键标记第一个点进入标定模式，然后**左键**标记第二个点完成 100m 距离标定，自动计算并填入参考像素值
- **全屏兼容** — （正在尝试制作测试）可选自动切换 PUBG 为无边框窗口模式（修改 `GameUserSettings.ini`）并处理全屏优化注册表标志
- **系统托盘** — 支持最小化到托盘，右键菜单可恢复窗口或完全退出
- **配置文件持久化** — 参考值、字体大小、窗口位置、兼容选项等均保存到本地 JSON 配置
- **字体可调** — 主界面可调整标注字体大小（10-80），实时生效
- **低侵入性 Hook** — 使用 `WH_KEYBOARD_LL` / `WH_MOUSE_LL`，所有输入通过 `CallNextHookEx` 原样传递，不影响游戏操作

## 系统要求

- Windows 10/11
- Python 3.8+（源码运行）或直接使用打包好的 `exe`
- PUBG 建议设置为**无边框窗口模式**（Borderless Windowed）

## 安装与运行

### 源码运行

```bash
pip install psutil
python pubg_ranging_tool.py
```

### 打包为 exe

```bash
pip install psutil pyinstaller
build_exe.bat
# 或手动执行:
pyinstaller --onefile --windowed --name "PUBG测距工具" --hidden-import psutil pubg_ranging_tool.py
```

输出文件位于 `dist/PUBG测距工具.exe`。

## 使用说明

| 操作 | 功能 |
|------|------|
| 程序启动 | 自动检测 PUBG，状态栏显示等待/运行状态 |
| 点击「我已启动游戏」| 跳过检测，立即激活覆盖层（调试模式） |
| `F8` | 呼出 / 关闭参考值输入菜单 |
| 右键/中键（任意组合）× 2 | 在地图上标记两个点，连线并计算距离 |
| 中键 → 左键 | 标定模式：中键标第一点 → 左键标第二点 → 自动填入参考值 |
| `M` / `Tab` / `Esc` | 关闭测距菜单 |
| 关闭窗口 | 弹出选项：最小化到托盘 / 完全退出 |
| 托盘右键 | 显示主窗口 / 完全退出 |

## 配置文件

程序在同目录下自动生成 `pubg_ranging_config.json`：

```json
{
  "reference": 150.0,
  "font_size": 22,
  "menu_x": 800,
  "menu_y": 0,
  "borderless_mode": false,
  "fullscreen_opt": false
}
```

## 注意事项

- **反作弊安全**：本工具仅使用 Windows 系统级 Hook（`WH_KEYBOARD_LL` / `WH_MOUSE_LL`），不注入游戏进程、不修改游戏内存、不 Hook DirectX，不会被 BattlEye 检测
- **覆盖层限制**：透明覆盖层在**独占全屏模式**下无法显示。请将 PUBG 设置为**无边框窗口模式**，或启用程序中的全屏兼容选项
- **管理员权限**：不需要。Hook 和覆盖窗口在普通用户权限下即可运行

## 项目结构

```
├── pubg_ranging_tool.py   # 主程序
├── requirements.txt       # Python 依赖
├── build_exe.bat          # 打包脚本
├── .gitignore
└── README.md
```

## License

MIT License
