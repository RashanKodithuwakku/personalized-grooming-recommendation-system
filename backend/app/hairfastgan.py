"""HairFastGAN adapter: remote Colab API or local subprocess."""

import os
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def get_status():
    api_url = os.getenv("HAIRFASTGAN_API_URL", "").strip().rstrip("/")
    api_token = os.getenv("HAIRFASTGAN_API_TOKEN", "").strip()

    if api_url:
        if not api_token:
            return {
                "configured": False,
                "message": "HAIRFASTGAN_API_TOKEN is missing.",
            }
        parsed = urlparse(api_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return {
                "configured": False,
                "message": "HAIRFASTGAN_API_URL must be a valid HTTPS URL.",
            }
        return {
            "configured": True,
            "mode": "remote_colab",
            "message": "Remote HairFastGAN API is configured.",
        }

    command = os.getenv("HAIRFASTGAN_COMMAND", "").strip()
    workdir = os.getenv("HAIRFASTGAN_WORKDIR", "").strip()

    if not command:
        return {
            "configured": False,
            "message": (
                "Set HAIRFASTGAN_API_URL and HAIRFASTGAN_API_TOKEN "
                "to use the Colab GPU API."
            ),
        }

    required = ("{input}", "{output}", "{reference}")
    missing = [token for token in required if token not in command]
    if missing:
        return {
            "configured": False,
            "message": (
                "HAIRFASTGAN_COMMAND must include {input}, {output}, "
                "and {reference} placeholders."
            ),
            "missing_placeholders": missing,
        }

    if workdir and not Path(workdir).expanduser().is_dir():
        return {
            "configured": False,
            "message": f"HAIRFASTGAN_WORKDIR does not exist: {workdir}",
        }

    return {
        "configured": True,
        "mode": "local_subprocess",
        "message": "Local HairFastGAN command is configured.",
    }


def run_advanced_preview(
    input_path,
    output_path,
    reference_path,
    style_name="selected_style",
    timeout_seconds=900,
):
    status = get_status()
    if not status["configured"]:
        raise RuntimeError(status["message"])

    source = Path(input_path).resolve()
    reference = Path(reference_path).resolve()
    destination = Path(output_path).resolve()

    if not source.is_file():
        raise FileNotFoundError(f"Input photo not found: {source}")
    if not reference.is_file():
        raise FileNotFoundError(
            f"Hairstyle reference image not found: {reference}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Remote mode: send images to the authenticated Colab GPU API.
    api_url = os.getenv("HAIRFASTGAN_API_URL", "").strip().rstrip("/")
    if api_url:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError(
                "The requests package is missing. Run: pip install requests"
            ) from exc

        headers = {
            "Authorization": (
                "Bearer " + os.getenv("HAIRFASTGAN_API_TOKEN", "").strip()
            )
        }

        try:
            with source.open("rb") as face_file, reference.open("rb") as ref_file:
                response = requests.post(
                    f"{api_url}/generate",
                    headers=headers,
                    files={
                        "face": (
                            source.name,
                            face_file,
                            "application/octet-stream",
                        ),
                        "reference": (
                            reference.name,
                            ref_file,
                            "application/octet-stream",
                        ),
                    },
                    timeout=(30, timeout_seconds),
                )

            if not response.ok:
                detail = response.text[:1500]
                raise RuntimeError(
                    f"Remote HairFastGAN API returned HTTP "
                    f"{response.status_code}: {detail}"
                )

            content_type = response.headers.get("content-type", "")
            if "image/" not in content_type.lower():
                raise RuntimeError(
                    "Remote API did not return an image. "
                    f"Content-Type: {content_type}; "
                    f"Response: {response.text[:500]}"
                )

            destination.write_bytes(response.content)

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Could not reach the Colab HairFastGAN API: {exc}"
            ) from exc

        if not destination.is_file() or destination.stat().st_size == 0:
            raise RuntimeError("Remote API returned an empty output image.")

        return str(destination)

    # Local mode: retain the previous subprocess behavior.
    command_template = os.environ["HAIRFASTGAN_COMMAND"]
    substitutions = {
        "{input}": str(source),
        "{output}": str(destination),
        "{reference}": str(reference),
        "{style}": str(style_name),
    }

    args = shlex.split(command_template, posix=(os.name != "nt"))
    args = [
        next(
            (
                arg.replace(token, value)
                for token, value in substitutions.items()
                if token in arg
            ),
            arg,
        )
        for arg in args
    ]

    workdir_value = os.getenv("HAIRFASTGAN_WORKDIR", "").strip()
    cwd = (
        str(Path(workdir_value).expanduser().resolve())
        if workdir_value
        else None
    )

    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"HairFastGAN exceeded the {timeout_seconds}-second timeout."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Could not start HairFastGAN: {exc}"
        ) from exc

    if completed.returncode != 0:
        detail = (
            completed.stderr or completed.stdout or "No diagnostic output"
        ).strip()[-3000:]
        raise RuntimeError(
            f"HairFastGAN failed ({completed.returncode}): {detail}"
        )

    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError(
            "HairFastGAN did not create the expected output image."
        )

    return str(destination)