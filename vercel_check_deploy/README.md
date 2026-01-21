# Vercel 배포 모니터링 스크립트

Vercel 프로젝트의 최신 배포 상태를 모니터링하고 결과를 출력하는 파이썬 스크립트입니다.

## 요구사항

- Python 3.6+
- requests 라이브러리

```bash
pip install requests
```

## 설정

### 1. Vercel API 토큰 발급

1. [Vercel Dashboard](https://vercel.com/account/tokens)에서 토큰 생성
2. 환경변수로 설정:

```bash
# Linux/Mac
export VERCEL_TOKEN=your_token_here

# Windows (PowerShell)
$env:VERCEL_TOKEN="your_token_here"

# Windows (CMD)
set VERCEL_TOKEN=your_token_here
```

## 사용법

### 기본 사용

```bash
python check_deploy.py <프로젝트명>
```

### 팀 계정 사용 시

```bash
python check_deploy.py <프로젝트명> --team-id team_xxxxx
```

## 예시

```bash
# 프로젝트 배포 상태 확인
python check_deploy.py my-awesome-project

# 팀 프로젝트 배포 상태 확인
python check_deploy.py my-team-project --team-id team_abc123
```

## 출력 예시

### 성공 시
```
🔍 프로젝트 'my-project'의 최신 배포를 조회 중...
📦 배포 ID: dpl_xxxxx
📊 초기 상태: BUILDING
⏳ 배포 진행 중... (1/10) - 30초 후 재확인

==================================================
✅ 배포 성공!
==================================================

✅ 배포 상태: READY
🔗 URL: https://my-project-xyz.vercel.app
📝 커밋: Fix bug in header (a1b2c3d)
```

### 실패 시
```
==================================================
❌ 배포 실패!
==================================================

❌ 배포 상태: ERROR
🔗 URL: https://my-project-xyz.vercel.app
📝 커밋: Update dependencies (d4e5f6g)
💥 에러 메시지: Build failed: Module not found
```

## 동작 방식

1. 프로젝트의 최신 배포를 조회
2. 배포 상태가 `BUILDING` 또는 `QUEUED`이면 30초마다 재확인 (최대 10회 = 5분)
3. 최종 상태에 따라 결과 출력:
   - `READY`: ✅ 성공 (종료 코드 0)
   - `ERROR`: ❌ 실패 (종료 코드 1)
   - 타임아웃: ⏰ 5분 초과 (종료 코드 2)

## 종료 코드

- `0`: 배포 성공
- `1`: 배포 실패 또는 오류
- `2`: 타임아웃 (5분 초과)

## CI/CD 통합 예시

### GitHub Actions

```yaml
- name: Vercel 배포 확인
  env:
    VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
  run: |
    python vercel_check_deploy/check_deploy.py my-project
```

### 일반 스크립트

```bash
#!/bin/bash

export VERCEL_TOKEN="your_token_here"

python check_deploy.py my-project

if [ $? -eq 0 ]; then
    echo "배포 완료! 후속 작업 진행..."
else
    echo "배포 실패! 롤백 필요..."
    exit 1
fi
```

## 문제 해결

### 인증 오류
```
❌ 인증 실패: VERCEL_TOKEN을 확인하세요.
```
→ VERCEL_TOKEN 환경변수가 올바른지 확인

### 프로젝트를 찾을 수 없음
```
❌ 프로젝트 'xxx'를 찾을 수 없습니다.
```
→ 프로젝트 이름 확인 또는 `--team-id` 옵션 추가

### 타임아웃
```
⏰ 타임아웃: 300초 동안 배포가 완료되지 않았습니다.
```
→ 배포가 비정상적으로 오래 걸리는 경우. Vercel Dashboard에서 직접 확인 필요
