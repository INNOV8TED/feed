#!/bin/bash
# =====================================================================
# GCP Heavy Parallel AI Batch Processor - Shell Launcher
# =====================================================================
# Designed to be run inside GCP terminal (Cloud Shell / Compute Engine VM)
# using standard GCP ADC credentials and Google Cloud available credits.
#
# Usage:
#   chmod +x execute_heavy_processor.sh
#   ./execute_heavy_processor.sh [target_directory] [workers] [limit]
# =====================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration Defaults
DEFAULT_PROJECT="studio-pulse-vault"
DEFAULT_REGION="us-central1"
DEFAULT_WORKERS=5
DEFAULT_LIMIT=0
DEFAULT_OUTPUT="vault_batch_catalog.json"

TARGET_DIR="${1:-.}"
WORKERS="${2:-$DEFAULT_WORKERS}"
LIMIT="${3:-$DEFAULT_LIMIT}"

echo "====================================================================="
echo "        GCP TERMINAL LAUNCHER: HEAVY PARALLEL AI PROCESSOR          "
echo "====================================================================="
echo "Target Directory : $TARGET_DIR"
echo "Concurrency Limit: $WORKERS threads"
echo "Limit Count      : $LIMIT"
echo "Output Catalog   : $DEFAULT_OUTPUT"
echo "====================================================================="

# Ensure we are logged into gcloud or have credentials
echo -e "\n[1/4] Checking Google Cloud SDK configuration..."
if ! command -v gcloud &> /dev/null; then
    echo "[WARNING] gcloud SDK not found in PATH. Ensure you are running in GCP environment or have installed gcloud."
else
    ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
    if [ -z "$ACTIVE_PROJECT" ] || [ "$ACTIVE_PROJECT" != "$DEFAULT_PROJECT" ]; then
        echo "[INFO] Setting active gcloud project to $DEFAULT_PROJECT..."
        gcloud config set project "$DEFAULT_PROJECT" || echo "[WARNING] Could not set project. Proceeding anyway..."
    else
        echo "[SUCCESS] Active GCP project is set to: $ACTIVE_PROJECT"
    fi
fi

# Set Region Environment Variables for Vertex AI
export CLOUDSDK_COMPUTE_REGION="$DEFAULT_REGION"
export CLOUDSDK_COMPUTE_ZONE="${DEFAULT_REGION}-a"

# Set up Python Virtual Environment
echo -e "\n[2/4] Setting up python virtual environment..."
VENV_DIR=".venv_gcp_processor"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Installing required packages
echo -e "\n[3/4] Installing / verifying required python dependencies..."
pip install --upgrade pip --quiet
pip install requests Pillow google-auth google-auth-oauthlib --quiet

# Check if ffmpeg is installed (for video processing)
echo -e "\n[Checking System Dependencies]"
if ! command -v ffmpeg &> /dev/null; then
    echo "[WARNING] ffmpeg is not installed on this system. Video frame extraction will fail."
    echo "To install ffmpeg on Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y ffmpeg"
else
    echo "[SUCCESS] ffmpeg is installed and available."
fi

# Executing Python Heavy Batch Processor
echo -e "\n[4/4] Launching high-throughput parallel batch processing script..."
echo "---------------------------------------------------------------------"
python3 gcp_heavy_processor.py "$TARGET_DIR" --workers "$WORKERS" --limit "$LIMIT" --output "$DEFAULT_OUTPUT"
echo "---------------------------------------------------------------------"

echo -e "\n[FINISHED] Execution complete. Results saved in $DEFAULT_OUTPUT"
