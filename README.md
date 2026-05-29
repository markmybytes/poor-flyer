# poor-flyer

<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->
<div align="center">

[![Tag][tag-shield]][tag-url]
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

</div>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/markmybytes/poor-flyer">
    <img src="https://github.com/markmybytes/poor-flyer/blob/main/src/static/favicon.svg" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">PoorFlyer 窮人想飛</h3>

  <p align="center">
    機票價格追蹤工具
    <br />
    <a href="https://github.com/markmybytes/poor-flyer/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/markmybytes/poor-flyer/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- ABOUT THE PROJECT -->

## 簡介

<p align="center">
  <img width="1114" height="352" alt="project screenshot" src="https://github.com/user-attachments/assets/2488805e-0bb7-42e5-8ae4-be88c17ccf8f" />
</p>

_PoorFlyer 窮人想飛_ 是一款專為精打細算旅客而設的機票價格追蹤工具。
程式每日會自動收集航空公司的最新票價，並整理成一目了然的價格走勢圖表，同時內置多種貨幣的匯率轉換，遇到外幣機票標價時亦毋須自行換算。

與一般只作簡單記錄的工具不同，PoorFlyer 內建了經典的 **[37% 法則（秘書問題）](https://zh.wikipedia.org/zh-hant/%E7%A7%98%E6%9B%B8%E5%95%8F%E9%A1%8C)** 算法。
透過「最佳停止理論」，程式會為你分析出最理性的購買時機。當最佳時機來臨，系統會發送電郵通知，助你以蔗渣價錢享受燒鵝味道。

程式亦支援 **Docker**，只需輸入幾行簡單指令，即可在自己的伺服器或 NAS 輕鬆架設專屬的個人機票追蹤面板。

<p align="right">(<a href="#readme-top">回到最頂</a>)</p>

### 建基於以下工具

[<img src="https://img.shields.io/badge/Flask-3BABC3?logo=flask&logoColor=fff&style=for-the-badge">](https://flask.palletsprojects.com/en/stable/)
[<img src="https://img.shields.io/badge/Iconify-026C9C?logo=iconify&logoColor=fff&style=for-the-badge">](https://iconify.design/)
[<img src="https://img.shields.io/badge/Inertia-9553E9?logo=inertia&logoColor=fff&style=for-the-badge">](https://inertiajs.com/)
[<img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=for-the-badge">](https://www.python.org/)
[<img src="https://img.shields.io/badge/Tailwind%20CSS-06B6D4?logo=tailwindcss&logoColor=fff&style=for-the-badge">](https://tailwindcss.com/)
[<img src="https://img.shields.io/badge/NuxtUI-00DC82?logo=nuxt&logoColor=fff&style=for-the-badge">](https://ui.nuxt.com/)
[<img src="https://img.shields.io/badge/Vue.js-4FC08D?logo=vuedotjs&logoColor=fff&style=for-the-badge">](https://vuejs.org/)

<p align="right">(<a href="#readme-top">回到最頂</a>)</p>

<!-- USAGE -->

## 使用指南

### 基本流程

1. **設定**
   - 選擇顯示貨幣
   - 設定電郵地址以接收提醒

2. **建立行程**
   - 輸入出發地、目的地和出發日期
   - 設定購票截止日期

3. **系統自動追蹤**
   - 每日自動更新價格
   - 當偵測到最佳時機時，發送電郵提醒

### 37% 法則

使用37% 法則（秘書問題）幫您分析最佳購買時機：

- **觀察階段**：在購票限期前 37% 的時間內，系統只觀察價格
- **買入信號**：之後如果價格降至歷史低點以下，您會收到提醒

<p align="right">(<a href="#readme-top">回到最頂</a>)</p>

<!-- DEPLOYMENT -->

## 部署

本項目可通過 Docker 部署。詳細的部署說明請參考項目文件。

<p align="right">(<a href="#readme-top">回到最頂</a>)</p>

<!-- GETTING STARTED -->

## 開發指南

### 所需軟件

- uv
- volta

### 安裝 Dependency

```bash
uv sync --all-extras
npm install
```

### 常用指令

**本地開發**

```bash
flask dev
```

**更新數據庫結構**

```bash
flask db migrate # 掃瞄數據庫結構改動並建立更新數據庫結構的指令碼
flask db upgrade # 建立數據庫／寫入新數據庫結構
```

**構建前端**

```bash
npm run build
```

**測試**

```bash
pytest
npm run test
```

<p align="right">(<a href="#readme-top">回到最頂</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[tag-url]: https://github.com/markmybytes/poor-flyer/releases
[tag-shield]: https://img.shields.io/github/v/tag/markmybytes/poor-flyer?style=for-the-badge&label=LATEST&color=%23B1B1B1
[contributors-shield]: https://img.shields.io/github/contributors/markmybytes/poor-flyer.svg?style=for-the-badge
[contributors-url]: https://github.com/markmybytes/poor-flyer/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/markmybytes/poor-flyer.svg?style=for-the-badge
[forks-url]: https://github.com/markmybytes/poor-flyer/network/members
[stars-shield]: https://img.shields.io/github/stars/markmybytes/poor-flyer.svg?style=for-the-badge
[stars-url]: https://github.com/markmybytes/poor-flyer/stargazers
[issues-shield]: https://img.shields.io/github/issues/markmybytes/poor-flyer.svg?style=for-the-badge
[issues-url]: https://github.com/markmybytes/poor-flyer/issues
[license-shield]: https://img.shields.io/github/license/markmybytes/poor-flyer.svg?style=for-the-badge
[license-url]: https://github.com/markmybytes/poor-flyer/blob/master/LICENSE.txt
