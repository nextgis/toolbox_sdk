import filecmp
from pathlib import Path

from toolbox_sdk import DownloadConfig, DownloadManager, ToolboxClient


def test_r_mapcalc(toolbox_client: ToolboxClient, tmp_path, monkeypatch):
    base = Path(__file__).parent

    mapcalc = toolbox_client.tool("r_mapcalc")
    result = mapcalc(
        {
            "A": toolbox_client.upload_file(base / "data/band4.tif"),
            "B": toolbox_client.upload_file(base / "data/band5.tif"),
            "expression": "A + B",
        }
    )

    # Download results using simple download manager
    simple_dir = tmp_path / "simple"
    simple_dir.mkdir()
    simple_files = toolbox_client.download_results(result, simple_dir)

    # Verify downloads
    assert len(simple_files) > 0
    assert all(p.exists() for p in simple_files.values())

    # Download results using parallel download manager
    parallel_dm = DownloadManager(toolbox_client, DownloadConfig(use_parallel=True))
    monkeypatch.setattr(toolbox_client, "download_manager", parallel_dm)

    parallel_dir = tmp_path / "parallel"
    parallel_dir.mkdir()
    parallel_files = toolbox_client.download_results(result, parallel_dir)

    # Compare with simple download manager results
    for k, v in parallel_files.items():
        assert filecmp.cmp(v, simple_files[k], shallow=False)
