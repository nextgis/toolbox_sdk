from pathlib import Path

from toolbox_sdk import ToolboxClient


def test_r_mapcalc(toolbox_client: ToolboxClient, tmp_path):
    base = Path(__file__).parent

    # Upload input files and run the mapcalc tool
    mapcalc = toolbox_client.tool("r_mapcalc")
    result = mapcalc(
        {
            "A": toolbox_client.upload_file(base / "data/band4.tif"),
            "B": toolbox_client.upload_file(base / "data/band5.tif"),
            "expression": "A + B",
        }
    )

    # Download results
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    toolbox_client.download_results(result, output_dir)

    # Get the downloaded file paths
    downloaded_files = result.get_all_file_paths()

    # Verify downloads
    assert len(downloaded_files) > 0
    assert all(p.exists() for p in downloaded_files.values())

    # Verify the result contains the expected output
    assert "result_raster" in downloaded_files
    assert downloaded_files["result_raster"].exists()
    assert downloaded_files["result_raster"].stat().st_size > 0
