**Language / 语言 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# 마우스 중앙 잠금

동영상 시청이나 게임 중 멀티태스킹 시 마우스 커서를 화면 중앙에 고정하는 Windows 유틸리티입니다. 전역 단축키, 트레이 메뉴, 간단/고급 UI, 다국어 지원, 재설정 주기/위치 설정을 지원합니다.

## 기능

- 전역 단축키 (사용자 정의): 잠금 / 잠금 해제 / 전환
- Minecraft 스타일 단축키 설정: 클릭 후 키 조합 직접 입력
- 트레이 아이콘 및 메뉴; 트레이로 최소화; Shift+닫기로 종료
- 간단/고급 모드
  - 고급: 단축키, 재설정 주기, 대상 위치 (가상 중앙, 기본 화면 중앙, 사용자 정의), 언어, 테마 설정
- 창 특정 잠금: 지정된 창이 활성화될 때만 잠금
- 창 전환 시 자동 잠금/해제
- 단일 인스턴스 감지: 중복 실행 방지
- 시작 시 실행
- 다국어: English, 简体中文, 繁體中文, 日本語, 한국어
- 라이트/다크 테마
- 다중 모니터 지원

## 프로젝트 구조

- `mouse_center_lock_gui.py` – GUI 앱 (PySide6)
- `win_api.py` – Windows API 래퍼 모듈
- `widgets.py` – 커스텀 UI 위젯 (단축키 캡처, 프로세스 선택기)
- `mouse_center_lock.py` – CLI/기본 버전 (선택사항)
- `pythonProject/i18n/` – 언어 파일
- `pythonProject/assets/` – 아이콘 및 리소스
- `config.json` – 기본 설정

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

가상 환경 생성 (권장) 후 윈도우 exe 빌드:
```bash
pyinstaller --noconfirm --clean --onefile --windowed \
  --name MouseCenterLock \
  --icon pythonProject/assets/app.ico \
  --add-data "pythonProject/i18n;i18n" \
  --add-data "config.json;." \
  --add-data "pythonProject/assets;assets" \
  --hidden-import win_api \
  --hidden-import widgets \
  mouse_center_lock_gui.py
```
exe 파일은 `dist/MouseCenterLock.exe`에 생성됩니다.

## 변경 기록

### v1.0.5
- 신규: 창 닫기 시 동작 묻기 (최소화/종료), "다시 묻지 않음" 옵션 지원
- 개선: 설정에 닫기 동작 초기화 옵션 추가
- 디버그: 창 특정 잠금 로직에 대한 디버그 로그 추가

### v1.0.4
- 버그 수정: "창 특정 잠금" 활성화 시 수동 잠금(단축키)이 창 제한을 우회하여 모든 창에서 잠기던 문제 수정
- 개선: 창 특정 잠금 활성화 시 엄격한 창 일치 확인

### v1.0.3
- Minecraft 스타일 단축키 설정: 입력 필드 클릭 후 키 조합 입력
- 단일 인스턴스 감지: 중복 실행 방지
- 시작 시 실행 옵션
- 프로세스 선택기에 검색 필터 추가
- 단축키 충돌 감지 및 경고
- 모듈화 아키텍처로 코드 리팩토링

### v1.0.2
- 라이트 테마 추가
- 창 전환 시 자동 잠금/해제

## 라이선스

MIT
