"""宿主机 HTTP 端口与草稿下载地址保持一致。"""

import importlib.util
import re
from pathlib import Path

import pytest

import config

# 直接加载模块，避免 src.service 包初始化拉起全部业务依赖。
_GET_DRAFT_PATH = Path(__file__).resolve().parents[1] / "src" / "service" / "get_draft.py"
_get_draft_spec = importlib.util.spec_from_file_location("get_draft_host_port_test", _GET_DRAFT_PATH)
_get_draft = importlib.util.module_from_spec(_get_draft_spec)
_get_draft_spec.loader.exec_module(_get_draft)
gen_download_url = _get_draft.gen_download_url

# AI-GEN-BEGIN
_COMPOSE_PATH = Path(__file__).resolve().parents[1] / "docker-compose.yaml"
_INTERPOLATION = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")


def interpolate_compose(value: str, env: dict) -> str:
    """按 Compose 单层 ${VAR:-default} 规则替换，不展开嵌套变量。

    Args:
        value: compose 文件中的原始字符串。
        env: 变量表。空字符串视为未设置，走默认值。

    Returns:
        替换后的字符串。
    """

    def replace(match: re.Match) -> str:
        name = match.group(1)
        has_default = match.group(2) is not None
        default = match.group(3) or ""
        current = env.get(name)
        if current is None or current == "":
            return default if has_default else ""
        return current

    return _INTERPOLATION.sub(replace, value)


def _compose_text() -> str:
    return _COMPOSE_PATH.read_text(encoding="utf-8")


def test_compose_binds_port_and_download_urls_to_one_variable():
    """端口映射、DRAFT_URL、DOWNLOAD_URL 必须引用同一个 HOST_HTTP_PORT。"""
    text = _compose_text()
    assert '"${HOST_HTTP_PORT:-80}:80"' in text
    assert "DRAFT_URL=http://127.0.0.1:${HOST_HTTP_PORT:-80}/openapi/capcut-mate/v1/get_draft" in text
    assert "DOWNLOAD_URL=http://127.0.0.1:${HOST_HTTP_PORT:-80}/" in text
    assert '"80:80"' not in text


def _quoted_assignments(rendered: str) -> dict:
    """提取 compose 环境项里的 KEY=VALUE，忽略注释中的示例。

    Args:
        rendered: 已完成变量替换的 compose 文本。

    Returns:
        环境变量名到值的映射。
    """
    return dict(re.findall(r'^\s*- "([A-Z0-9_]+)=([^"]+)"\s*$', rendered, re.M))


@pytest.mark.parametrize(
    ("env", "port_mapping", "draft_url", "download_url"),
    [
        (
            {},
            "80:80",
            "http://127.0.0.1:80/openapi/capcut-mate/v1/get_draft",
            "http://127.0.0.1:80/",
        ),
        (
            {"HOST_HTTP_PORT": "81"},
            "81:80",
            "http://127.0.0.1:81/openapi/capcut-mate/v1/get_draft",
            "http://127.0.0.1:81/",
        ),
    ],
)
def test_compose_interpolation_keeps_port_and_urls_aligned(env, port_mapping, draft_url, download_url):
    """复现 issue #59：发布 81 时下载地址必须带 :81；默认仍映射 80。"""
    rendered = interpolate_compose(_compose_text(), env)
    assignments = _quoted_assignments(rendered)
    assert assignments["DRAFT_URL"] == draft_url
    assert assignments["DOWNLOAD_URL"] == download_url
    assert f'- "{port_mapping}"' in rendered


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "http://127.0.0.1:80/openapi/capcut-mate/v1/get_draft",
            "http://127.0.0.1/openapi/capcut-mate/v1/get_draft",
        ),
        ("http://127.0.0.1:80/", "http://127.0.0.1/"),
        ("http://127.0.0.1:80", "http://127.0.0.1"),
        (
            "http://127.0.0.1:81/openapi/capcut-mate/v1/get_draft",
            "http://127.0.0.1:81/openapi/capcut-mate/v1/get_draft",
        ),
        ("http://127.0.0.1:81/", "http://127.0.0.1:81/"),
        ("http://127.0.0.1:8080/output/a.json", "http://127.0.0.1:8080/output/a.json"),
        ("https://capcut-mate.jcaigc.cn/", "https://capcut-mate.jcaigc.cn/"),
        ("http://127.0.0.1/openapi/capcut-mate/v1/get_draft", "http://127.0.0.1/openapi/capcut-mate/v1/get_draft"),
    ],
)
def test_strip_loopback_http_default_port(raw, expected):
    """默认 :80 还原为旧 URL，非 80 端口保留。"""
    assert config.strip_loopback_http_default_port(raw) == expected


def test_gen_download_url_includes_non_default_host_port(monkeypatch):
    """DOWNLOAD_URL 带宿主机端口时，草稿文件下载地址必须带上该端口。"""
    monkeypatch.setattr(config, "PROJECT_ROOT", "/app")
    monkeypatch.setattr(config, "DOWNLOAD_URL", "http://127.0.0.1:81/")
    url = gen_download_url("/app/output/draft/abc/draft_info.json")
    assert url == "http://127.0.0.1:81/output/draft/abc/draft_info.json"
# AI-GEN-END
