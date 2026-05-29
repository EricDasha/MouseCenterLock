**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

# MouseControlLayer

MouseControlLayer는 커서 잠금, 자동 클릭, 간단한 매크로 동작을 다루는 Windows 마우스 / 키보드 제어 도구입니다.

처음에는 마우스를 화면 중앙에 고정하는 작은 도구였지만, 실제 사용 중 자동 클릭, 단축키, 창별 규칙, 매크로가 필요해지면서 현재 구조로 확장되었습니다.

## 기능

### 마우스 잠금

가상 화면 중앙, 기본 모니터 중앙, 현재 창 중앙 또는 사용자 지정 위치로 커서를 고정할 수 있습니다.

### 자동 클릭과 프로필

토글 / 홀드 트리거, 클릭 간격, 프로세스 블랙리스트, 시작 효과음, 여러 프로필을 지원합니다. **더보기** 메뉴에서 프로필을 가져오기, 내보내기, 삭제, 전체 초기화할 수 있습니다. 저장하지 않은 변경이 있는 상태에서 프로필을 바꾸면 저장 여부를 묻습니다.

### 간단한 매크로

마우스 클릭, 키 누름 / 떼기, 지연, 단축키, 텍스트 입력을 순서대로 실행할 수 있습니다. 기본 `F12` 강제 중지 키로 실행 중이거나 토글 중인 매크로를 멈추고 눌린 출력을 해제할 수 있습니다.

### 창 규칙

특정 창이 활성화되어 있을 때만 잠금, 자동 클릭, 매크로 동작을 적용할 수 있습니다.

## 요구 사항

- Windows 10+
- Python 3.9+
- 종속성: `requirements.txt`

```bash
python -m pip install -r requirements.txt
python mouse_center_lock_gui.py
python -m unittest discover tests
```

## 빌드

```bash
python build.py
```

exe는 `dist/MCL.exe`에 생성됩니다. 로컬 release zip은 `release/`에 생성되며, zip 내부 파일명은 `MouseControlLayer.exe`입니다.

## 마우스 매크로 설정

- [마우스 매크로 예제 및 설정 설명](examples/mouse-macros/ko/README.md)
- [입력 백엔드 로드맵](docs/backend-roadmap.md)

## 알려진 제한

주로 Windows API / SendInput 기반의 사용자 계층 입력입니다. 관리자 권한 창, Raw Input 게임, 안티치트 보호 게임, 시뮬레이션 입력을 거부하는 프로그램에서는 동작하지 않을 수 있습니다.

## 입력 백엔드

`native-sendinput`, `python-sendinput`, `window-message`를 사용할 수 있습니다. `virtual-hid`와 `hardware-hid`는 향후 확장을 위해 예약되어 있습니다.

## 프로젝트 구조

- `mouse_center_lock_gui.py` – GUI 앱
- `win_api.py` – Windows API 래퍼
- `services/` – 런타임 서비스
- `ui/pages/` – 페이지 빌더
- `tests/` – 테스트
- `i18n/` – 언어 파일
- `examples/mouse-macros/` – 매크로 예제

## 변경 기록

[CHANGELOG.md](CHANGELOG.md)

## 라이선스

[GPL-3.0](LICENSE)
