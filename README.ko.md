**언어 / Language / 语言**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# 마우스 중앙 잠금

비디오를 시청하거나 게임 중 멀티태스킹할 때 마우스 커서를 화면 중앙에 고정하는 Windows 유틸리티입니다. 전역 단축키, 트레이 메뉴, 간단/고급 UI, 다국어 지원 및 재중앙화 빈도/위치 설정이 가능합니다.

## 기능
- 전역 단축키 (사용자 정의 가능): 잠금 / 잠금 해제 / 토글
- 트레이 아이콘 및 메뉴; 트레이로 닫기; Shift+닫기로 종료
- 간단/고급 모드
  - 고급: 단축키, 재중앙화 간격, 대상 위치 (가상 중앙, 주 화면 중앙, 사용자 정의), 언어 사용자 정의
- 다국어 지원: English, 简体中文, 繁體中文, 日本語, 한국어
- 다중 모니터 지원

## 프로젝트 구조
- `mouse_center_lock_gui.py` – GUI 앱 (PySide6)
- `mouse_center_lock.py` – CLI/기본 버전 (선택 사항)
- `pythonProject/i18n/` – 언어 파일
- `pythonProject/assets/` – 아이콘 및 리소스 (`app.ico`를 여기에 배치)
- `config.json` – 기본 설정 (사용자 설정은 exe 옆에 기록됨)
- `pythonProject/create_icon.py` – 이미지에서 다중 크기 `.ico`를 생성하는 도우미 (Pillow)

## 요구 사항
- Windows 10+
- Python 3.9+
- 종속성: `requirements.txt` 참조

종속성 설치:
```bash
python -m pip install -r requirements.txt
```

실행:
```bash
python mouse_center_lock_gui.py
```

## 빌드 (PyInstaller)
가상 환경을 생성하고 (권장) 창 모드 exe를 빌드합니다:
```bash
pyinstaller --noconfirm --clean --onefile --windowed \
  --name MouseCenterLock \
  --icon pythonProject/assets/app.ico \
  --add-data "pythonProject/i18n;i18n" \
  --add-data "config.json;." \
  --add-data "pythonProject/assets;assets" \
  mouse_center_lock_gui.py
```
exe 파일은 `dist/MouseCenterLock.exe`에 생성됩니다.

## 사용자 정의 아이콘
다중 크기 `app.ico`를 `pythonProject/assets/`에 배치하세요. 앱과 트레이가 자동으로 사용합니다. 없으면 내장 벡터 아이콘이 사용됩니다.

PNG/JPG에서 `app.ico` 생성:
```bash
python pythonProject/create_icon.py <input_image> pythonProject/assets/app.ico
```

## 라이선스
MIT

