import asyncio
import json
import os
import re
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig








async def main():
    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig(
        excluded_tags=['form', 'header', 'img', 'link', 'a'],
        exclude_external_links=True,
        process_iframes=False,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://www.gadgets360.com/mobiles/reviews/oneplus-nord-ce-4-lite-review-5954674",
            config=run_config
        )

        if result.success:
            review_content = result.markdown.strip()
            cleaned_md = re.sub(r"^\* \[.*?\]\(.*?\)\n?", "", review_content, flags=re.MULTILINE)

            # Append to Markdown file
            with open("results.md", "a", encoding="utf-8") as md_file:
                md_file.write(f"\n\n## {result.url}\n\n{cleaned_md}\n")

            # Append to JSON file
            json_data = {
                "url": result.url,
                "content": review_content
            }

            existing_data = []
            if os.path.exists("results.json"):
                with open("results.json", "r", encoding="utf-8") as json_file:
                    try:
                        existing_data = json.load(json_file)
                    except json.JSONDecodeError:
                        pass  # Treat as empty if file is invalid

            if not isinstance(existing_data, list):
                existing_data = [existing_data]

            existing_data.append(json_data)

            with open("results.json", "w", encoding="utf-8") as json_file:
                json.dump(existing_data, json_file, indent=4, ensure_ascii=False)

            print("Scraping completed. Data appended to results.md and results.json")

        else:
            print(f"Crawl failed: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
