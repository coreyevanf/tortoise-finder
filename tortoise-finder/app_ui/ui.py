import os
import gradio as gr
import requests
import math

API = os.environ.get("API_URL", "http://api:8000")

def start_run(dataset_uri, threshold):
    r = requests.post(f"{API}/run", json={"dataset_uri": dataset_uri, "threshold": threshold})
    r.raise_for_status()
    data = r.json()
    return data["run_id"], gr.update(visible=True)

def poll_status(run_id):
    r = requests.get(f"{API}/status/{run_id}")
    r.raise_for_status()
    s = r.json()
    return f'{s["state"]} — {s["progress_pct"]:.1f}%'

def fetch_page(run_id, threshold, page, page_size):
    r = requests.get(f"{API}/positives", params={"run_id": run_id, "threshold": threshold, "page": page, "page_size": page_size})
    r.raise_for_status()
    d = r.json()
    gallery = [(it["thumb_url"], f'{it["tile_id"]} | {it["score"]:.3f} | {it["lat"]:.5f},{it["lon"]:.5f}') for it in d["items"]]
    pages = max(1, math.ceil(d["total"] / page_size))
    return gallery, f"Total: {d['total']} | Page {page}/{pages}"

def export_file(run_id, fmt):
    r = requests.get(f"{API}/export", params={"run_id": run_id, "fmt": fmt})
    r.raise_for_status()
    return r.json()["url"]

with gr.Blocks(title="Tortoise Finder") as demo:
    gr.Markdown("## Tortoise Finder — MVP")
    with gr.Row():
        dataset_uri = gr.Textbox(value=os.getenv("DEFAULT_DATASET_URI", "s3://tortoise-artifacts/datasets/demo"), label="Dataset URI")
        thr = gr.Slider(0, 1, step=0.01, value=0.8, label="Threshold")
        run_btn = gr.Button("Start Run")
    run_id = gr.Textbox(label="Run ID", interactive=False)
    status = gr.Textbox(label="Status", interactive=False)
    status_timer = gr.Timer(1.5, active=False)
    review_panel = gr.Column(visible=False)
    with review_panel:
        with gr.Row():
            page = gr.Number(value=1, precision=0, label="Page")
            page_size = gr.Dropdown(choices=[20, 40, 80], value=40, label="Page size")
            refresh = gr.Button("Refresh")
        gallery = gr.Gallery(label="Positives", columns=6, height=600, full_screen=True)
        tally = gr.Markdown()
        with gr.Row():
            fmt = gr.Dropdown(choices=["geojson", "csv", "gpx", "kml"], value="geojson", label="Export format")
            export_btn = gr.Button("Export")
            url = gr.Textbox(label="Download URL")

    # Ensure Detection Results are only shown in the Detection tab
    run_btn.click(start_run, [dataset_uri, thr], [run_id, review_panel])
    status_timer.tick(lambda rid: poll_status(rid), [run_id], [status])
    run_btn.click(lambda: gr.update(active=True), None, status_timer)
    refresh.click(fetch_page, [run_id, thr, page, page_size], [gallery, tally])
    thr.release(fetch_page, [run_id, thr, page, page_size], [gallery, tally])
    export_btn.click(export_file, [run_id, fmt], [url])

    # Add event listeners for confirm and reject buttons
    confirm_btn = gr.Button("Confirm")
    reject_btn = gr.Button("Reject")
    confirm_btn.click(lambda img_id: confirm_image(img_id), [gallery.selected], None)
    reject_btn.click(lambda img_id: reject_image(img_id), [gallery.selected], None)

    # JavaScript for rapid navigation and full-screen view
    <script>
        document.addEventListener('keydown', function(event) {
            if (event.key === 'ArrowRight') {
                // Navigate to next image
                gallery.next();
            } else if (event.key === 'ArrowLeft') {
                // Navigate to previous image
                gallery.prev();
            }
        });
    </script>

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
