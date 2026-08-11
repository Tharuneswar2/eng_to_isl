#!/usr/bin/env python3
"""
English → ISL Translator — Gradio Web UI

Launch with:
    python app.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from eng_to_isl import config
from eng_to_isl.translator import ISLTranslator

config.setup_logging()

# Initialize translator globally (reused across requests)
translator = ISLTranslator()


def translate_to_isl(text: str):
    """Translate English text to ISL and return results for Gradio."""
    if not text or not text.strip():
        return "Please enter some text.", "", None

    result = translator.translate(text)

    # Build gloss display
    gloss_display = " ".join(result.gloss) if result.gloss else "—"

    # Build sign lookup report
    report_lines = []
    for g in result.gloss:
        g_lower = g.lower()
        if g_lower in result.found:
            sign = result.found[g_lower]
            report_lines.append(f"  {g:15s} ✓  ({sign.word})")
        else:
            report_lines.append(f"  {g:15s} ✗  MISSING")

    if result.missing:
        report_lines.append("")
        report_lines.append("Missing signs:")
        for m in result.missing:
            report_lines.append(f"  • {m}")

    if result.errors:
        report_lines.append("")
        report_lines.append("Errors:")
        for e in result.errors:
            report_lines.append(f"  • {e}")

    report = "\n".join(report_lines) if report_lines else "—"

    # Build info text
    info_parts = [
        f"ISL Gloss: {gloss_display}",
        "",
        "Sign Lookup:",
        report,
    ]
    info_text = "\n".join(info_parts)

    # Video output
    video_path = None
    if result.output_video and result.output_video.exists():
        video_path = str(result.output_video)

    return info_text, gloss_display, video_path


def main():
    try:
        import gradio as gr
    except ImportError:
        print("ERROR: Gradio not installed.")
        print("Install with: pip install gradio")
        sys.exit(1)

    with gr.Blocks(
        title="English → ISL Translator",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "# 🤟 English → Indian Sign Language Translator\n"
            "Enter English text and get the corresponding ISL sign video."
        )

        with gr.Row():
            with gr.Column(scale=1):
                text_input = gr.Textbox(
                    label="Enter English text",
                    placeholder="I need water",
                    lines=2,
                )
                translate_btn = gr.Button(
                    "Translate",
                    variant="primary",
                    size="lg",
                )

                gloss_output = gr.Textbox(
                    label="ISL Gloss",
                    interactive=False,
                )

                info_output = gr.Textbox(
                    label="Translation Details",
                    lines=10,
                    interactive=False,
                )

            with gr.Column(scale=1):
                video_output = gr.Video(
                    label="ISL Video Output",
                )

        translate_btn.click(
            fn=translate_to_isl,
            inputs=[text_input],
            outputs=[info_output, gloss_output, video_output],
        )

        text_input.submit(
            fn=translate_to_isl,
            inputs=[text_input],
            outputs=[info_output, gloss_output, video_output],
        )

        gr.Markdown(
            "---\n"
            "**Dataset**: bridgeconn/sign-dictionary-isl "
            "(CC BY-SA) · Bridge Connectivity Solutions Pvt. Ltd.\n\n"
            "**Note**: This is a prototype using rule-based gloss "
            "conversion. ISL grammar ordering is approximate."
        )

    demo.launch(share=False)


if __name__ == "__main__":
    main()
