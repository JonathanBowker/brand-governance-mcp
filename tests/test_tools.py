import pytest
from fastmcp.server.tasks.config import TaskConfig

from src.errors import CapabilityLockedError
from src.tools.access import run_brand_check_access
from src.tools.answer import run_brand_answer_question
from src.tools.content import run_brand_get_content, run_brand_list_content
from src.tools.images import run_brand_get_image_list
from src.tools.index import run_brand_get_index
from src.tools.list import run_brand_list_standards
from src.tools.rules import run_brand_get_rules
from src.tools.standard import run_brand_get_standard
from src.workflows.tasking import optional_task_config, supports_background_tasks
from tests.conftest import JSON_KEY, TOOLKIT_KEY, VALID_KEY


async def test_brand_get_index(s3_env):
    response = await run_brand_get_index(VALID_KEY)
    assert response["ok"] is True
    assert response["brand"] == "PwC"


async def test_brand_list_standards(s3_env):
    response = await run_brand_list_standards(VALID_KEY, category="visual")
    assert response["count"] == 4


async def test_brand_get_standard_markdown(s3_env):
    response = await run_brand_get_standard(VALID_KEY, "logo", "markdown")
    assert response["standardId"] == "logo"
    assert "Clear space" in response["content"]


async def test_brand_get_standard_defaults_to_markdown_without_json_access(s3_env):
    response = await run_brand_get_standard(VALID_KEY, "logo")
    assert response["standardId"] == "logo"
    assert response["format"] == "markdown"
    assert response["requestedFormat"] == "auto"
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
    assert response["manifestSource"] == "directory"
    assert response["images"][0]["filename"] == "logo.png"
    assert "imageUrl" in response["images"][0]
    assert response["images"][0]["imageUrl"].startswith("https://advancedanalytica.co.uk/")
    assert response["images"][0]["url"] == response["images"][0]["imageUrl"]
    assert response["images"][0]["src"] == response["images"][0]["imageUrl"]
    assert response["images"][0]["thumbnailUrl"] == response["images"][0]["imageUrl"]
    assert response["images"][0]["alt"] == "Primary logo example"
    assert "presignedUrl" not in response["images"][0]
    assert response["images"][0]["assetType"] == "logo_variant"
    assert response["images"][0]["variant"] == "full_lockup"
    assert response["images"][0]["colourway"] == "colour_positive"
    assert response["images"][0]["section"] == "Approved variants"
    assert response["images"][0]["approvedBackgrounds"] == ["white", "light_gradient", "light_photography"]
    assert response["images"][0]["minSize"]["digitalPx"] == 48
    assert response["images"][0]["clearspaceRule"] == "Height of the lowercase c in the wordmark."


async def test_brand_get_image_list_uses_master_manifest_when_local_manifest_missing(s3_env):
    response = await run_brand_get_image_list(VALID_KEY, "grid-system")
    assert response["count"] == 1
    assert response["manifestSource"] == "master"
    assert response["masterManifestPath"] == "advanced-user/master-image-manifest.json"
    assert response["manifestPath"] == "advanced-user/standards/grid-system/images/manifest.json"
    assert response["images"][0]["filename"] == "grid.png"
    assert response["images"][0]["title"] == "Standard 12x12 page layout grid"
    assert response["images"][0]["description"] == "Reference image showing the approved layout grid."
    assert response["images"][0]["section"] == "Standard grid"
    assert response["images"][0]["usage"] == "primary reference"
    assert response["images"][0]["tags"] == ["grid-system", "page-layout", "12x12-grid"]


async def test_brand_answer_question(s3_env):
    response = await run_brand_answer_question(VALID_KEY, "What is the logo clear space?", mode="concise")
    assert response["ok"] is True
    assert "Logo" in response["answer"]


async def test_brand_get_standard_json_with_layer_3_access(s3_env):
    response = await run_brand_get_standard(JSON_KEY, "data-visualisation", "json")
    assert response["standardId"] == "data-visualisation"
    assert '"contexts": {"levels": ["level_1", "level_2"]}' in response["content"]


async def test_brand_get_standard_defaults_to_json_with_layer_3_access(s3_env):
    response = await run_brand_get_standard(JSON_KEY, "data-visualisation")
    assert response["standardId"] == "data-visualisation"
    assert response["format"] == "json"
    assert response["requestedFormat"] == "auto"
    assert '"contexts": {"levels": ["level_1", "level_2"]}' in response["content"]


async def test_brand_answer_question_prefers_json_sidecar_when_available(s3_env):
    response = await run_brand_answer_question(JSON_KEY, "What should I use for level_1 charts?", mode="detailed")
    assert response["ok"] is True
    assert "Matched applicability:" in response["answer"]
    assert "Token Level 1 palette: Use solid orange and grey tints for level_1 charts." in response["answer"]
    assert response["standardsUsed"][0]["sourceType"] == "json"
    assert "level_1" in response["standardsUsed"][0]["matchedApplicability"]
    assert response["standardsUsed"][0]["related"] == ["standard.colour", "standard.typography"]


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
    assert response["images"][0]["imageUrl"].startswith("https://advancedanalytica.co.uk/")
    assert response["images"][0]["url"] == response["images"][0]["imageUrl"]
    assert response["images"][0]["src"] == response["images"][0]["imageUrl"]
    assert response["images"][0]["thumbnailUrl"] == response["images"][0]["imageUrl"]
    assert response["images"][0]["alt"] == "social.png"


def test_optional_task_config_matches_runtime():
    config = optional_task_config()
    if supports_background_tasks():
        assert isinstance(config, TaskConfig)
        assert config.mode == "optional"
    else:
        assert config is False
