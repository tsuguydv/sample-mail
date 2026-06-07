from __future__ import annotations

from pathlib import Path

from examples.sample_emails import (
    build_b2b_saas_email,
    build_cart_abandonment_email,
    build_case_study_email,
    build_corporate_email,
    build_ecommerce_email,
    build_event_invitation_email,
    build_newsletter_email,
    build_onboarding_email,
    build_product_launch_email,
    build_promo_email,
    build_reactivation_email,
    build_service_offer_email,
    build_welcome_email,
)


EXAMPLES = {
    "b2b_saas.html": build_b2b_saas_email,
    "ecommerce.html": build_ecommerce_email,
    "corporate.html": build_corporate_email,
    "promo.html": build_promo_email,
    "welcome.html": build_welcome_email,
    "product_launch.html": build_product_launch_email,
    "event_invitation.html": build_event_invitation_email,
    "newsletter.html": build_newsletter_email,
    "cart_abandonment.html": build_cart_abandonment_email,
    "reactivation.html": build_reactivation_email,
    "onboarding.html": build_onboarding_email,
    "case_study.html": build_case_study_email,
    "service_offer.html": build_service_offer_email,
}


def get_available_path(output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = output_dir / f"{stem}_{counter:03d}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def main() -> None:
    output_dir = Path("output/examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []

    for filename, factory in EXAMPLES.items():
        output_path = get_available_path(output_dir, filename)
        output_path.write_text(factory(), encoding="utf-8")
        created_files.append(output_path)

    print(f"Generated {len(created_files)} example emails in {output_dir}")
    for path in created_files:
        print(f"- {path}")


if __name__ == "__main__":
    main()
