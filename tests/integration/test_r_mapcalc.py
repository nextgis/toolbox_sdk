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
    toolbox_client.download_results(result, simple_dir)

    # Get the downloaded file paths
    simple_files = result.get_all_file_paths()

    # Verify downloads
    assert len(simple_files) > 0
    assert all(p.exists() for p in simple_files.values())

    # Create a new result object for parallel download to avoid mixing file paths
    parallel_result = mapcalc(
        {
            "A": toolbox_client.upload_file(base / "data/band4.tif"),
            "B": toolbox_client.upload_file(base / "data/band5.tif"),
            "expression": "A + B",
        }
    )

    # Download results using parallel download manager
    parallel_dm = DownloadManager(toolbox_client, DownloadConfig(use_parallel=True))
    monkeypatch.setattr(toolbox_client, "download_manager", parallel_dm)

    parallel_dir = tmp_path / "parallel"
    parallel_dir.mkdir()
    toolbox_client.download_results(parallel_result, parallel_dir)

    # Get the downloaded file paths
    parallel_files = parallel_result.get_all_file_paths()

    # Compare with simple download manager results
    assert len(simple_files) == len(parallel_files)

    # Compare file contents (need to match by output name since paths are different)
    for output_name in simple_files.keys():
        simple_path = simple_files[output_name]
        parallel_path = parallel_files[output_name]
        assert filecmp.cmp(simple_path, parallel_path, shallow=False)
