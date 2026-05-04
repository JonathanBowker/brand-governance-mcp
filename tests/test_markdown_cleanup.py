from src.utils.markdown_cleanup import strip_shared_header_block


def test_strip_shared_header_block_removes_advanced_user_preamble():
    raw = """## Welcome to the Brand Site for advanced users

READ AND AGREE BEFORE YOU ENTER THE SITE

![](./images/Video_poster_BrandExplainer.png)

We are pleased to grant you access.

Submit

- [Key points](#key-points)

# **Bids and proposals**

Body content here.
"""

    cleaned, changed = strip_shared_header_block(raw)

    assert changed is True
    assert cleaned.startswith("# **Bids and proposals**")
    assert "Welcome to the Brand Site for advanced users" not in cleaned


def test_strip_shared_header_block_leaves_normal_markdown_alone():
    raw = """# **Logo**

Body content here.
"""

    cleaned, changed = strip_shared_header_block(raw)

    assert changed is False
    assert cleaned == raw
