# GoProcure

A collection of tools for downloading and organizing GoPro media from its cloud service.

## Tools

- `gopro-download`: Download media files from GoPro Cloud
- `gopro-organize`: Organize local media files by date and update their metadata to reflect the actual capture date
- `gopro-sync`: Download and organize files in one step

## Installation

1. Clone the repository:
```bash
git clone https://github.com/aricha/gopro-tools.git
cd gopro-tools
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make scripts executable:
```bash
chmod +x gopro-download gopro-organize gopro-sync
```

## Usage

### Download from Cloud

```bash
./gopro-download --output-dir DIR [options]
  --include-photos    # Include photos
  --max-items N      # Limit number of items
  --download-gpmf    # Download GPMF data
  --verbose          # Verbose logging
```

NOTE: To download from GoPro Cloud, you first need to provide credentials by creating a `config.json` file formatted like so:

```json
{
  "access_token": "your-token",
  "user_id": "your-user-id"
}
```

To determine your access token and user ID:

1. Log into the GoPro site
2. Open up your browser's Developer Inspector and navigate to the Network tab
3. Set up a filter for `user`
4. Refresh the page or click on a video
5. Once a `user` network request to `api.gopro.com` occurs, click on one of them and look at the Cookies field
6. Extract the `access_token` and `user_id` cookie parameters and save them to your `config.json`

Note that the access token is temporary and only has a TTL of a few hours, so you may need to repeat this process occasionally.

### Organize Local Files

```bash
./gopro-organize DIR [options]
  --copy            # Copy instead of move
  --recursive       # Process subdirectories
  --dry-run        # Show what would be done
  --verbose        # Verbose logging
```

### Download and Organize

```bash
./gopro-sync --output-dir DIR [options]
  # Supports most options from both tools above
```