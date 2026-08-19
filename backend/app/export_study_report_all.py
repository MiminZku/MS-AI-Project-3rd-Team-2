from __future__ import annotations

import sys
import traceback

from app.export_study_report_bi import main as export_bi
from app.export_study_report_word import main as export_word


def run_export(
    name: str,
    export_function,
) -> bool:

    print()
    print("=" * 60)
    print(f"{name} 생성 시작")
    print("=" * 60)

    try:
        export_function()

        print()
        print(f"[완료] {name}")

        return True

    except PermissionError as error:

        print()
        print(f"[실패] {name}")
        print()
        print(
            "출력 파일이 Excel 또는 Word에서 "
            "열려 있을 가능성이 있습니다."
        )
        print(
            "열려 있는 파일을 닫고 다시 실행해주세요."
        )
        print()
        print(f"오류: {error}")

        return False

    except Exception as error:

        print()
        print(f"[실패] {name}")
        print()
        print(f"오류: {error}")
        print()

        traceback.print_exc()

        return False


def main() -> None:

    print()
    print("=" * 60)
    print("Study Report Export")
    print("=" * 60)

    print()
    print(
        "Study 분석 결과를 "
        "Word 리포트와 Power BI용 Excel로 변환합니다."
    )

    word_success = run_export(
        "Word Research Report",
        export_word,
    )

    bi_success = run_export(
        "Power BI Dataset",
        export_bi,
    )

    print()
    print("=" * 60)
    print("Export 결과")
    print("=" * 60)

    print(
        "Word Report : "
        + (
            "성공"
            if word_success
            else "실패"
        )
    )

    print(
        "Power BI Excel : "
        + (
            "성공"
            if bi_success
            else "실패"
        )
    )

    print()

    if (
        word_success
        and bi_success
    ):

        print(
            "전체 Study Report Export 완료"
        )

        print()
        print(
            "생성 파일:"
        )

        print(
            "app\\ai-interview-report"
            "\\study_report.docx"
        )

        print(
            "app\\ai-interview-report"
            "\\study_report_powerbi.xlsx"
        )

        return

    print(
        "일부 Export가 실패했습니다."
    )

    sys.exit(1)


if __name__ == "__main__":
    main()