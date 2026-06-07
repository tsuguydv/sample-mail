from __future__ import annotations

from pathlib import Path

from examples.sample_emails import build_b2b_saas_email


def main() -> None:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    html = build_b2b_saas_email()
    (output_dir / "email.html").write_text(html, encoding="utf-8")
    print("Email saved to output/email.html")


if __name__ == "__main__":
    main()
