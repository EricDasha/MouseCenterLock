# 마우스 매크로 예제

이 폴더에는 고급 설정 → Mouse Macros → External JSON file 에서 선택할 수 있는 JSON 예제가 있습니다.

## 예제 파일

- `right-left-left-2-1.json`: 오른쪽 버튼을 누른 채 왼쪽 클릭 → 왼쪽 클릭, 상단 숫자 `2`, 상단 숫자 `1`.
- `x1-left-copy.json`: `x1` 뒤로가기 사이드 버튼을 누른 채 왼쪽 클릭 → `Ctrl+C`.
- `x2-left-paste-enter.json`: `x2` 앞으로가기 사이드 버튼을 누른 채 왼쪽 클릭 → `Ctrl+V`, `Enter`.
- `middle-right-text.json`: 가운데 버튼을 누른 채 오른쪽 클릭 → `GG` 입력, 80ms 대기, `Enter`.
- `key-delay-key.json`: 키보드 `A`를 누른 채 `B`를 누를 때마다 → `A`, 50ms 대기, `B`; `A`를 계속 누른 상태에서 `B`를 반복 입력하면 반복 실행됩니다.

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

## 키보드 트리거 규칙

외부 JSON은 키보드 hold/press 규칙도 지원합니다.

```json
{
  "holdKey": "A",
  "pressKey": "B",
  "actions": [
    { "type": "key", "key": "A" },
    { "type": "delay", "ms": 50 },
    { "type": "key", "key": "B" }
  ]
}
```

`A`를 계속 누른 상태에서 `B`를 새로 누를 때마다 액션 시퀀스가 다시 실행됩니다.

## 액션 타입

- `hotkey`, `key`, `mouseClick`, `text`, `delay`
