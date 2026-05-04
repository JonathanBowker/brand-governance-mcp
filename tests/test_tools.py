import pytest

from src.errors import CapabilityLockedError
from src.tools.access import run_brand_check_access
from src.tools.answer import run_brand_answer_question
from src.tools.content import run_brand_get_content, run_brand_list_content
from src.tools.images import run_brand_get_image_list
from src.tools.index import run_brand_get_index
from src.tools.list import run_brand_list_standards
from src.tools.rules import run_brand_get_rules
from src.tools.standard import run_brand_get_standard
from tests.conftest import TOOLKIT_KEY, VALID_KEY


async def test_brand_get_index(s3_env):
    response = await run_brand_get_index(VALID_KEY)
    assert response["ok"] is True
    assert response["brand"] == "PwC"


async def test_brand_list_standards(s3_env):
    response = await run_brand_list_standards(VALID_KEY, category="visual")
    assert response["count"] == 2


async def test_brand_get_standard_markdown(s3_env):
    response = await run_brand_get_standard(VALID_KEY, "logo", "markdown")
    assert response["standardId"] == "logo"
    assert "Clear space" in response["content"]


async def test_brand_get_standard_no_yaml_access(s3_env):
    with pytest.raises(CapabilityLockedError):
        await run_brand_get_standard(VALID_KEY, "logo", "yaml")


async def test_brand_get_rules(s3_env):
    response = await run_brand_get_rules(VALID_KEY, "logo")
    assert "Minimum size is 48px digital" in response["keyRules"]


async def test_brand_check_access(s3_env):
    response = await run_brand_check_access(VALID_KEY)
    assert response["clientId"] == "pwc"
    assert response["accessControl"]["standards"] is True


async def test_brand_get_image_list(s3_env):
    response = await run_brand_get_image_list(VALID_KEY, "logo")
    assert response["count"] == 1
    assert response["images"][0]["filename"] == "logo.png"
    assert "presignedUrl" in response["images"][0]


async def test_brand_answer_question(s3_env):
    response = await run_brand_answer_question(VALID_KEY, "What is the logo clear space?", mode="concise")
    assert response["ok"] is True
    assert "Logo" in response["answer"]


async def test_brand_list_content_toolkits(s3_env):
    response = await run_brand_list_content(TOOLKIT_KEY, group="toolkits")
    assert response["ok"] is True
    assert response["count"] == 1
    assert response["content"][0]["id"] == "toolkits/social-media"


async def test_brand_get_content_toolkit_markdown(s3_env):
    response = await run_brand_get_content(TOOLKIT_KEY, "toolkits/social-media", "markdown")
    assert response["contentId"] == "toolkits/social-media"
    assert "approved branded templates" in response["content"]


async def test_brand_get_content_toolkit_denied_without_access(s3_env):
    with pytest.raises(CapabilityLockedError):
        await run_brand_get_content(VALID_KEY, "toolkits/social-media", "markdown")


async def test_brand_get_image_list_toolkit(s3_env):
    response = await run_brand_get_image_list(TOOLKIT_KEY, "toolkits/social-media")
    assert response["count"] == 1
    assert response["images"][0]["filename"] == "social.png"
