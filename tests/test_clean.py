"""Tests for the HTML cleaner."""

from __future__ import annotations

from pathlib import Path

from src.clean import clean


def test_drops_navigation_and_footer(tmp_path: Path):
    html = """
    <html><head><title>Test</title></head>
    <body>
        <nav><a href="/">Home</a> <a href="/about">About</a></nav>
        <header>Site Header</header>
        <main>
            <h1>What is coronary CTA</h1>
            <p>Coronary CT angiography uses a CT scanner to take pictures of
            the arteries that supply blood to your heart.</p>
            <p>You will lie on a table that moves through the scanner.</p>
        </main>
        <footer>Copyright 2025. All rights reserved.</footer>
    </body></html>
    """
    result = clean("test-page", html, tmp_path)
    assert "Coronary CT angiography" in result.cleaned_text
    assert "Site Header" not in result.cleaned_text
    assert "Copyright" not in result.cleaned_text
    assert result.word_count > 10
    assert result.cleaned_path.exists()


def test_drops_references_section(tmp_path: Path):
    html = """
    <html><body><main>
    <p>The procedure uses iodinated contrast material.</p>
    <p>References:</p>
    <p>1. Smith J, Jones B, et al. Cardiac CT review. Journal of Cardiology. 2020;1:1-10.</p>
    <p>2. Brown A, et al. Imaging methods. Radiology. 2021;200:55-60.</p>
    </main></body></html>
    """
    result = clean("test-refs", html, tmp_path)
    assert "iodinated contrast" in result.cleaned_text
    assert "Smith J" not in result.cleaned_text


def test_normalizes_smart_quotes(tmp_path: Path):
    html = "<html><body><main><p>Don’t worry, you’ll be fine.</p></main></body></html>"
    result = clean("test-quotes", html, tmp_path)
    assert "’" not in result.cleaned_text
    assert "'" in result.cleaned_text
