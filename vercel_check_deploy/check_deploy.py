#!/usr/bin/env python3
"""
Vercel 배포 상태 모니터링 스크립트

사용법:
    python check_deploy.py                        # 팀 전체 최신 배포 모니터링
    python check_deploy.py <프로젝트명>           # 특정 프로젝트 최신 배포 모니터링
    python check_deploy.py --team-id <팀ID>       # 팀 전체, 특정 팀 ID 사용
    python check_deploy.py <프로젝트명> --team-id <팀ID>

설정:
    config.py에서 VERCEL_TOKEN, VERCEL_TEAM_ID 읽어옴
"""

import sys
import time
import argparse
import requests
from typing import Optional, Dict, Any
from config import VERCEL_TOKEN, VERCEL_TEAM_ID

# 설정 상수
VERCEL_API_BASE = "https://api.vercel.com"
POLL_INTERVAL = 30  # 초
MAX_POLLS = 10  # 최대 폴링 횟수 (30초 * 10 = 5분)

# 배포 상태별 이모지
STATUS_EMOJI = {
    "READY": "✅",
    "ERROR": "❌",
    "BUILDING": "🔨",
    "QUEUED": "⏳",
    "CANCELED": "🚫",
    "INITIALIZING": "🔄"
}


class VercelDeploymentMonitor:
    """Vercel 배포 모니터링 클래스"""

    def __init__(self, token: str, team_id: Optional[str] = None):
        """
        Args:
            token: Vercel API 토큰
            team_id: 팀 ID (선택)
        """
        self.token = token
        self.team_id = team_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get_latest_deployment(self, project_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        프로젝트의 최신 배포를 가져옴

        Args:
            project_name: 프로젝트 이름 (None이면 팀 전체 최신 배포)

        Returns:
            배포 정보 딕셔너리 또는 None
        """
        url = f"{VERCEL_API_BASE}/v6/deployments"
        params = {
            "limit": 1
        }

        # project_name이 있으면 프로젝트 필터 추가
        if project_name:
            params["projectId"] = project_name

        if self.team_id:
            params["teamId"] = self.team_id

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            deployments = data.get("deployments", [])

            if not deployments:
                if project_name:
                    print(f"⚠️  프로젝트 '{project_name}'의 배포를 찾을 수 없습니다.")
                else:
                    print("⚠️  팀의 배포를 찾을 수 없습니다.")
                return None

            return deployments[0]

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                if project_name:
                    print(f"❌ 프로젝트 '{project_name}'를 찾을 수 없습니다.")
                else:
                    print("❌ 팀을 찾을 수 없습니다.")
            elif e.response.status_code == 401:
                print("❌ 인증 실패: config.py의 VERCEL_TOKEN을 확인하세요.")
            else:
                print(f"❌ API 오류: {e}")
            return None

        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return None

    def get_deployment_details(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """
        배포 상세 정보를 가져옴

        Args:
            deployment_id: 배포 ID

        Returns:
            배포 상세 정보 딕셔너리 또는 None
        """
        url = f"{VERCEL_API_BASE}/v13/deployments/{deployment_id}"
        params = {}

        if self.team_id:
            params["teamId"] = self.team_id

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"❌ 배포 상세 정보 조회 실패: {e}")
            return None

    def print_deployment_info(self, deployment: Dict[str, Any]):
        """
        배포 정보를 출력

        Args:
            deployment: 배포 정보 딕셔너리
        """
        state = deployment.get("state", "UNKNOWN")
        emoji = STATUS_EMOJI.get(state, "❓")
        url = deployment.get("url", "N/A")
        commit = deployment.get("meta", {}).get("githubCommitMessage", "N/A")
        commit_sha = deployment.get("meta", {}).get("githubCommitSha", "")

        if commit_sha:
            commit_sha_short = commit_sha[:7]
            commit_info = f"{commit} ({commit_sha_short})"
        else:
            commit_info = commit

        print(f"\n{emoji} 배포 상태: {state}")
        print(f"🔗 URL: https://{url}")
        print(f"📝 커밋: {commit_info}")

        # 에러가 있으면 출력
        if state == "ERROR":
            error_message = deployment.get("errorMessage")
            if error_message:
                print(f"💥 에러 메시지: {error_message}")

    def monitor_deployment(self, project_name: Optional[str] = None) -> int:
        """
        배포를 모니터링하고 결과를 반환

        Args:
            project_name: 프로젝트 이름 (None이면 팀 전체 최신 배포)

        Returns:
            종료 코드 (0: 성공, 1: 실패, 2: 타임아웃)
        """
        if project_name:
            print(f"🔍 프로젝트 '{project_name}'의 최신 배포를 조회 중...")
        else:
            print("🔍 팀 전체의 최신 배포를 조회 중...")

        # 최신 배포 조회
        deployment = self.get_latest_deployment(project_name)
        if not deployment:
            return 1

        deployment_id = deployment.get("uid")
        state = deployment.get("state")
        project_info = deployment.get("name", "unknown")

        print(f"📦 배포 ID: {deployment_id}")
        print(f"📂 프로젝트: {project_info}")
        print(f"📊 초기 상태: {state}")

        # 배포 상태 폴링
        poll_count = 0
        while state in ["BUILDING", "QUEUED", "INITIALIZING"]:
            if poll_count >= MAX_POLLS:
                print(f"\n⏰ 타임아웃: {MAX_POLLS * POLL_INTERVAL}초 동안 배포가 완료되지 않았습니다.")
                self.print_deployment_info(deployment)
                return 2

            poll_count += 1
            print(f"⏳ 배포 진행 중... ({poll_count}/{MAX_POLLS}) - {POLL_INTERVAL}초 후 재확인")
            time.sleep(POLL_INTERVAL)

            # 배포 상태 재확인
            deployment = self.get_deployment_details(deployment_id)
            if not deployment:
                return 1

            state = deployment.get("state")

        # 최종 결과 출력
        if state == "READY":
            print("\n" + "="*50)
            print("✅ 배포 성공!")
            print("="*50)
            self.print_deployment_info(deployment)
            return 0

        elif state == "ERROR":
            print("\n" + "="*50)
            print("❌ 배포 실패!")
            print("="*50)
            self.print_deployment_info(deployment)
            return 1

        elif state == "CANCELED":
            print("\n" + "="*50)
            print("🚫 배포가 취소되었습니다.")
            print("="*50)
            self.print_deployment_info(deployment)
            return 1

        else:
            print(f"\n❓ 알 수 없는 상태: {state}")
            self.print_deployment_info(deployment)
            return 1


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Vercel 배포 상태를 모니터링합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python check_deploy.py                        # 팀 전체 최신 배포
    python check_deploy.py my-project             # 특정 프로젝트
    python check_deploy.py --team-id team_xxxxx   # 팀 전체, 특정 팀
    python check_deploy.py my-project --team-id team_xxxxx

설정:
    config.py에서 VERCEL_TOKEN, VERCEL_TEAM_ID 읽어옴
        """
    )

    parser.add_argument(
        "project_name",
        nargs="?",
        default=None,
        help="모니터링할 Vercel 프로젝트 이름 (생략 시 팀 전체 최신 배포)"
    )

    parser.add_argument(
        "--team-id",
        help="Vercel 팀 ID (기본값: config.py의 VERCEL_TEAM_ID)"
    )

    args = parser.parse_args()

    # config.py에서 토큰 읽기
    if not VERCEL_TOKEN:
        print("❌ 오류: config.py에 VERCEL_TOKEN이 설정되지 않았습니다.")
        print("\n설정 방법:")
        print("  config.py 파일에서 VERCEL_TOKEN을 설정하세요.")
        sys.exit(1)

    # team_id: 인자가 없으면 config.py 기본값 사용
    team_id = args.team_id if args.team_id else VERCEL_TEAM_ID

    # 모니터링 시작
    monitor = VercelDeploymentMonitor(VERCEL_TOKEN, team_id)
    exit_code = monitor.monitor_deployment(args.project_name)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
