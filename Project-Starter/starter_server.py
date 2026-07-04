
from fileinput import filename
import os
import json
import logging
from typing import List, Dict, Optional
from unittest import result
from firecrawl import FirecrawlApp
from urllib.parse import urlparse
from datetime import datetime
from mcp.server.fastmcp import FastMCP

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCRAPE_DIR = "scraped_content"

mcp = FastMCP("llm_inference")

@mcp.tool()
def scrape_websites(
    websites: Dict[str, str],
    formats: List[str] = ['markdown', 'html'],
    api_key: Optional[str] = None
) -> List[str]:
    """
    Scrape multiple websites using Firecrawl and store their content.
    
    Args:
        websites: Dictionary of provider_name -> URL mappings
        formats: List of formats to scrape ['markdown', 'html'] (default: both)
        api_key: Firecrawl API key (if None, expects environment variable)
        
    Returns:
        List of provider names for successfully scraped websites
    """
    
    if api_key is None:
        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            raise ValueError("API key must be provided or set as FIRECRAWL_API_KEY environment variable")
    
    app = FirecrawlApp(api_key=api_key)
    
    path = os.path.join(SCRAPE_DIR)
    os.makedirs(path, exist_ok=True)
    
    # save the scraped content to files and then create scraped_metadata.json as a summary file
    # check if the provider has already been scraped and decide if you want to overwrite
    # {
    #     "cloudrift_ai": {
    #         "provider_name": "cloudrift_ai",
    #         "url": "https://www.cloudrift.ai/inference",
    #         "domain": "www.cloudrift.ai",
    #         "scraped_at": "2025-10-23T00:44:59.902569",
    #         "formats": [
    #             "markdown",
    #             "html"
    #         ],
    #         "success": "true",
    #         "content_files": {
    #             "markdown": "cloudrift_ai_markdown.txt",
    #             "html": "cloudrift_ai_html.txt"
    #         },
    #         "title": "AI Inference",
    #         "description": "Scraped content goes here"
    #     }
    # }
    metadata_file = os.path.join(path, "scraped_metadata.json")
    
    # continue your solution here ...
    successful_scrapes = []
    
    # Load existing metadata if it exists
    try:    
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        scraped_metadata = {}
    
    # Iterate over the websites and scrape them
    for provider_name, url in websites.items():
        logger.info(f"Scraping {provider_name} at {url}")
        
        metadata = {
            "provider_name": provider_name,
            "url": url,
            "domain": "",
            "scraped_at": "",
            "formats": formats,
            "success": True,
            "content_files": {},
            "title": "",
            "description": ""}
        try:
            scrape_result = app.scrape(url, formats=formats).model_dump()
            scraped_at = datetime.utcnow().isoformat()
            domain = urlparse(url).netloc
            
            # Save the scraped content to files
            if scrape_result.get('success', False):
                for format in formats:
                    content = scrape_result.get(format, "")
                    file_name = f"{provider_name}_{format}.txt"
                    file_path = os.path.join(SCRAPE_DIR, file_name)
                    
                    with open(file_path, 'w') as f:
                        f.write(content)
            
                    metadata["content_files"][format] = file_name
                
                metadata["scraped_at"] = scraped_at
                metadata["domain"] = domain
                metadata["title"] = scrape_result.get("title", "")
                metadata["description"] = scrape_result.get("description", "")
                metadata["success"] = True
            
                successful_scrapes.append(provider_name)
            else:
                metadata["success"] = False
                logger.warning(f"Scraping failed for {provider_name} at {url}")
        
        except Exception as e:
            logger.error(f"Failed to scrape {provider_name} at {url}: {e}")
        finally:
            scraped_metadata[provider_name] = metadata
            
    with open("scraped_metadata.json", 'w') as f:
        json.dump(scraped_metadata, f)
    
    logger.info(f"Scraping completed. Successful scrapes: {successful_scrapes}")

    return successful_scrapes
    

@mcp.tool()
def extract_scraped_info(identifier: str) -> str:
    """
    Extract information about a scraped website.
    
    Args:
        identifier: The provider name, full URL, or domain to look for
        
    Returns:
        Formatted JSON string with the scraped information
    """
    
    logger.info(f"Extracting information for identifier: {identifier}")
    logger.info(f"Files in {SCRAPE_DIR}: {os.listdir(SCRAPE_DIR)}")

    metadata_file = os.path.join(SCRAPE_DIR, "scraped_metadata.json")
    logger.info(f"Checking metadata file: {metadata_file}")

    # contine your response here ...
    try:
        # Load scraped metadata
        with open(metadata_file, 'r') as f:
            scraped_metadata = json.load(f)
        
        # Extract information based on the identifier
        for provider_name, metadata in scraped_metadata.items():
            url = metadata.get("url", "")
            domain = metadata.get("domain", "")
            
            if identifier in [provider_name, url, domain]:
                result = metadata.copy()
                
                if result.get("content_files"):
                    result["content"] = {}
                    for format, file_name in result["content_files"].items():
                        content_file_path = os.path.join(SCRAPE_DIR, file_name)
                        with open(content_file_path, 'r') as f:
                            result["content"][format] = f.read()
                return json.dumps(result, indent=4)
            
    except Exception as e:
        logger.error(f"Error occurred while extracting scraped info: {e}")
    return f"No scraped information found for identifier: {identifier}"        
        

if __name__ == "__main__":
    mcp.run(transport="stdio")