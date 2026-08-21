from summary_bot.summarizer import Summarizer


def test_render_html_and_real_links_only():
    raw = "Срок запуска || Запуск назначен на среду || 2, 1\nБюджет || Требует согласования || 3"
    rendered = Summarizer._render(raw, {1: "https://t.me/c/123/10", 2: "https://t.me/c/123/11"})

    assert "<b>Срок запуска</b>" in rendered
    assert "**" not in rendered
    assert 'href="https://t.me/c/123/11"' in rendered
    assert 'href="https://t.me/c/123/10"' in rendered
    assert "источник 3" not in rendered


def test_render_escapes_model_html():
    rendered = Summarizer._render("<b>Опасное</b> || A & B ||", {})
    assert "&lt;b&gt;Опасное&lt;/b&gt;" in rendered
    assert "A &amp; B" in rendered
