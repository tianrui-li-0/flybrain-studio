# First public release / 第一次开源

Current local build: `release-official/FlyBrainStudio/FlyBrainStudio.exe`.

## 先发布什么

GitHub 仓库存放源码、README、LICENSE、THIRD_PARTY、依赖版本、构建脚本和测试。Releases 存放 Windows 压缩包。不要把虚拟环境、build、release、缓存、私人路径、测试视频或动画片段提交到 Git。

## 数据许可先核实

本项目代码 MIT 不覆盖 FlyWire 科学数据。官方公开数据采用 CC BY-NC 4.0，需署名并遵守非商业限制，见 THIRD_PARTY。源码仓库只提供直接下载官方文件的脚本、转换器和来源清单；生成的 NPZ 与原始 CSV 均被 Git 忽略。桌面压缩包包含科学数据，数据许可与运行库声明也随包保留。

## GitHub 操作顺序

1. 注册 / 登录 GitHub，点击 New repository。起一个名字，如 FlyBrainStudio，填一句准确简介，选择 Public。
2. 在本地准备干净源码目录。先检查文件清单及许可证；不要上传整个包含 work、release 和个人实验的父目录。
3. 用 GitHub Desktop 的 Add local repository / Create repository 管理源码，检查 Changes，确认无个人文件，然后提交并 Publish repository。
4. README 放实际截图、三步启动方法、功能和模型限制。用“真实连接组上的实验性视听 LIF 模拟器”，不要称为验证过的果蝇色觉、听觉或意识。
5. 在 Releases 创建 v0.1.0，说明 Windows 版本和已测试功能。将整个可执行程序文件夹压缩，而不是只上传 exe。保留 _internal 与第三方声明。上传 ZIP 及 SHA-256 校验值。
6. 发布前在新的解压目录测试双击启动、视频输入、音轨、导出。明确自建程序没有代码签名，不声称通过平台认证。
7. 仓库准备好后再发帖子，链接到 README 或 Release。演示涉及的动画内容不要随代码分发。

本次只完成本地准备，没有创建公共仓库、上传文件或发帖。

## 此项目的本地 Git 目录

本地仓库就是 FlyBrainStudio 文件夹，远程为 https://github.com/tianrui-li-0/flybrain-studio 。
`release*`、`build`、原始下载和生成的数据文件不会进入源码提交。不要拖动整个输出目录上传。
在 GitHub Desktop 中使用 File → Add local repository，选择此文件夹，再查看 Changes 和 Push origin。
如果 GitHub 要求登录，在自己的 GitHub 登录窗口完成，不要把密码或令牌发进聊天。

从 Git 克隆后按 README 安装依赖，再运行 download_data.py、prepare_data.py，即可启动。
代码和数据都准备好后才打包 Windows 版；新打包目录是 release-official。

## English overview

FlyBrain Studio is a local Windows application for inspecting a FlyWire-derived
connectome and running approximate LIF dynamics driven by experimental visual
and auditory inputs. It preserves real neuron IDs and annotation positions.
RGB receptor assignments and auditory frequency preferences are artificial,
not physiologically calibrated. It does not reproduce consciousness, fear,
or a validated biological response to a movie.

Source and Windows binaries should be distributed separately. Verify scientific
data redistribution terms before publishing the bundled dataset. Keep all
applicable dependency notices with binary releases.
