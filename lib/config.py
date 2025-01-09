import logging

def setup_logging(verbose: bool = False):
    """Configure logging."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )