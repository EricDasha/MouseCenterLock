# 마우스 매크로 예제

이 폴더에는 고급 설정 → Macro → External JSON file 에서 선택할 수 있는 JSON 예제가 있습니다.

## 목차

- [예제 파일](#예제-파일)
- [규칙 항목](#규칙-항목)
- [마우스 버튼 이름](#마우스-버튼-이름)
- [키보드 `key` 이름](#키보드-key-이름)
- [액션 타입](#액션-타입)

## 예제 파일

- `right-left-left-2-1.json`: 오른쪽 버튼을 누른 채 왼쪽 클릭 → 왼쪽 클릭, 상단 숫자 `2`, 상단 숫자 `1`.
- `x1-left-copy.json`: `x1` 뒤로가기 사이드 버튼을 누른 채 왼쪽 클릭 → `Ctrl+C`.
- `x2-left-paste-enter.json`: `x2` 앞으로가기 사이드 버튼을 누른 채 왼쪽 클릭 → `Ctrl+V`, `Enter`.
- `middle-right-text.json`: 가운데 버튼을 누른 채 오른쪽 클릭 → `GG` 입력, 80ms 대기, `Enter`.
- `middle-left-test.json`: 실행 중 진단용. 가운데 버튼을 누른 채 왼쪽 클릭 → 상단 숫자 `1`.
- `back-left-2-delay-1.json`: `back` / `x1` 을 누른 채 왼쪽 클릭 → `2`, 100ms, `1`. 왼쪽 클릭 자체는 실제 입력을 통과시킴.
- `key-delay-key.json`: `A`를 누른 채 `B`를 누를 때마다 → `A`, 50ms, `B`.
- `repeat-r-on-1-off-2.json`: `1`로 100ms마다 `R` 입력, `2`로 중지.
- `left-hold-repeat-r-on-1-off-2.json`: `1`로 감지 시작, 왼쪽 버튼을 누르는 동안 100ms마다 `R`, `2`로 중지.

## 규칙 항목

```json
{
  "id": "rule-id",
  "name": "Rule name",
  "enabled": true,
  "triggerMode": "hold",
  "holdMouseButton": "x1",
  "pressMouseButton": "left",
  "actions": [],
  "onCancel": [],
  "cooldownMs": 0,
  "loopIntervalMs": 1
}
```

### `triggerMode`

| 값 | 의미 |
|---|---|
| `hold` | 누르고 있는 동안, 트리거 버튼을 한 번 누르면 1회 실행 |
| `toggle` | 한 번 눌러 armed, 이후 트리거로 실행 |
| `holdLoop` | 누르고 있는 동안 동작 목록을 반복 실행 |
| `toggleLoop` | 한 번 눌러 반복 시작, 다시 한 번 눌러 정지 |

### Safety stop

`panicHotkey` 는 앱 전체 설정입니다. 기본값은 `F12`이며, 실행/토글 중인 매크로를 강제로 중지하고 눌린 출력을 해제합니다.

## 마우스 버튼 이름

| 설정값 | 실제 버튼 |
|---|---|
| `left` | 왼쪽 버튼 |
| `right` | 오른쪽 버튼 |
| `middle` | 가운데 / 휠 버튼 |
| `x1` | 사이드 버튼 1, 보통 Back |
| `x2` | 사이드 버튼 2, 보통 Forward |

> `back` / `forward` 는 사용할 수 없습니다. `x1` / `x2` 를 사용하세요.

## 키보드 `key` 이름

- 문자: `A` ~ `Z`
- 상단 숫자: `0` ~ `9` (숫자패드 아님)
- 기능키: `F1` ~ `F24`
- 특수키: `Space`, `Tab`, `Enter`, `Backspace`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Up`, `Down`, `Left`, `Right`

## 액션 타입

- `hotkey`
- `key`
- `keyDown` / `keyUp`
- `mouseClick`
- `mouseDown` / `mouseUp`
- `text`
- `delay`
