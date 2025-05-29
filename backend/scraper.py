# import asyncio
# import json
# import os
# import re
# from crawl4ai import AsyncWebCrawler
# from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig


# async def main():
#     browser_config = BrowserConfig()
#     run_config = CrawlerRunConfig(
#         excluded_tags=['form', 'header', 'img', 'link', 'a'],
#         exclude_external_links=True,
#         process_iframes=False,
#         remove_overlay_elements=True,
#     )

#     async with AsyncWebCrawler(config=browser_config) as crawler:
#         result = await crawler.arun(
#             url="https://www.gadgets360.com/mobiles/reviews/motorola-edge-50-fusion-review-6320432",
#             config=run_config
#         )

#         if result.success:
#             review_content = result.markdown.strip()
#             cleaned_md = re.sub(r"^\* \[.*?\]\(.*?\)\n?", "", review_content, flags=re.MULTILINE)

#             # Append to Markdown file
#             with open("results.md", "a", encoding="utf-8") as md_file:
#                 md_file.write(f"\n\n## {result.url}\n\n{cleaned_md}\n")

#             # Append to JSON file
#             json_data = {
#                 "url": result.url,
#                 "content": review_content
#             }

#             existing_data = []
#             if os.path.exists("results.json"):
#                 with open("results.json", "r", encoding="utf-8") as json_file:
#                     try:
#                         existing_data = json.load(json_file)
#                     except json.JSONDecodeError:
#                         pass  # Treat as empty if file is invalid

#             if not isinstance(existing_data, list):
#                 existing_data = [existing_data]

#             existing_data.append(json_data)

#             with open("results.json", "w", encoding="utf-8") as json_file:
#                 json.dump(existing_data, json_file, indent=4, ensure_ascii=False)

#             print("Scraping completed. Data appended to results.md and results.json")

#         else:
#             print(f"Crawl failed: {result.error_message}")


# if __name__ == "__main__":
#     asyncio.run(main())
import asyncio
import json
import os
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

def extract_product_info(content, url):
    """Extract product name and price from content"""
    product_info = {"product_name": "", "price": "", "url": url}

    # Extract product name
    title_patterns = [
        r'^#\s+(.+?)\s+Review',
        r'##\s+(.+?)\s+Review',
        r'^(.+?)\s+Review:\s+',
        r'^The\s+(.+?)\s+is\s+'
    ]

    for pattern in title_patterns:
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        if match:
            name = re.sub(r'^(The\s+)', '', match.group(1).strip(), flags=re.IGNORECASE)
            if len(name) > 5:
                product_info["product_name"] = name
                break

    # Extract price
    price_match = re.search(r'(?:priced?\s+(?:from\s+)?|costs?\s+|starts\s+at\s+)Rs\.?\s*([\d,]+)', content, re.IGNORECASE)
    if price_match:
        product_info["price"] = f"Rs. {price_match.group(1)}"

    return product_info

def extract_pros_cons(content):
    """Extract pros and cons from review"""
    pros, cons = [], []

    # Look for Good/Bad or Pros/Cons sections
    patterns = [
        r'(?:Good|Pros)[:\s]*\n(.*?)(?:Bad|Cons)[:\s]*\n(.*?)(?=\n#{1,3}|\Z)',
        r'(?:Pros)[:\s]*\n(.*?)(?:Cons)[:\s]*\n(.*?)(?=\n#{1,3}|\Z)'
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            pros_text = match.group(1).strip()
            pros = [line.strip('• -* ').strip() for line in pros_text.split('\n')
                   if line.strip() and len(line.strip()) > 5]

            cons_text = match.group(2).strip()
            cons = [line.strip('• -* ').strip() for line in cons_text.split('\n')
                   if line.strip() and len(line.strip()) > 5]
            break

    return pros[:5], cons[:5]  # Limit to 5 each

def extract_verdict(content):
    """Extract final verdict"""
    patterns = [
        r'(?:Verdict|Conclusion|Final Thoughts?)[:\s]*\n(.*?)(?=\n#{1,3}|\Z)',
        r'(?:Final Verdict|Our Verdict)[:\s]*\n(.*?)(?=\n#{1,3}|\Z)'
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            verdict = re.sub(r'\*+', '', match.group(1).strip())
            return re.sub(r'\n+', ' ', verdict).strip()
    return ""

def clean_content(content):
    """Remove unwanted elements from content"""

    unwanted_patterns = [
        # Navigation and UI
        r"^\* \[.*?\]\(.*?\)\n?", r"English Edition.*?\n", r"More\s*\n", r"Comments?\n",
        r"Snapchat Comment\n?", r"Advertisement\n?", r"Highlights\s*\n",

        # Author and meta info
        r"Written by.*?IST\n", r"Email\s+[A-Za-z\s]+\n", r"[A-Za-z\s]+is based in.*?\.\.\.\s*\n",

        # Social media and promotional
        r"For the latest.*?\.\s*\n", r"Follow Us\n", r"Popular on Gadgets\n", r"Download Our Apps\n",
        r"Available in Hindi\n", r"\*\s*Flat ₹\d+.*?\n", r"\*\s*Extra.*?\n",

        # Footer and legal
        r"© Copyright.*?reserved\.\n", r"\*\s*Sponsored\s*\n", r"Search for.*?\n",

        # Review navigation
        r"\*\s*(?:REVIEW|KEY SPECS|NEWS|Design|Display|Software|Performance|Battery Life|Camera|Value for Money|Good|Bad)\s*\n",

        # Tech specs summary
        r"Read detailed\s*\n", r"(?:Display|Front Camera|Rear Camera|RAM|Storage|Battery Capacity|OS|Resolution) .*?\n",

        # Price lists and repeated elements
        r"\*\s*₹[\d,]+\s*\n", r"Related Stories.*?\n", r"Close \[X\]\n",

        # Image captions
        r"\(tap.*?expand\)", r"\(tap.*?larger.*?\)",

        # Cleanup
        r"\n\s*\*\s*\n", r"\n{3,}", r"^\s*\n"
    ]

    cleaned = content
    for pattern in unwanted_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)

    return re.sub(r'\n{3,}', '\n\n', cleaned).strip()

def format_for_rag(content, url):
    """Format content for RAG optimization"""

    cleaned_content = clean_content(content)
    product_info = extract_product_info(cleaned_content, url)
    pros, cons = extract_pros_cons(cleaned_content)
    verdict = extract_verdict(cleaned_content)

    # Build structured markdown
    structured_md = f"""---

## {product_info['product_name']} Review

**Product:** {product_info['product_name']}
**Price:** {product_info['price']}
**Source:** {url}

### Review Content
{cleaned_content}
"""

    # Add pros/cons if found
    if pros or cons:
        structured_md += "\n### Pros & Cons\n"
        if pros:
            structured_md += "**Pros:**\n" + "\n".join(f"- {pro}" for pro in pros) + "\n"
        if cons:
            structured_md += "\n**Cons:**\n" + "\n".join(f"- {con}" for con in cons) + "\n"

    # Add verdict if found
    if verdict:
        structured_md += f"\n### Final Verdict\n{verdict}\n"

    return structured_md, {
        "product_info": product_info,
        "pros": pros,
        "cons": cons,
        "verdict": verdict,
        "word_count": len(cleaned_content.split()),
        "scraped_date": datetime.now().isoformat()
    }

async def main():
    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig(
        excluded_tags=['form', 'header', 'img', 'link', 'a', 'nav', 'footer', 'aside', 'script', 'style'],
        exclude_external_links=True,
        process_iframes=False,
        remove_overlay_elements=True,
        exclude_social_media_links=True,
    )

    urls = [
        "https://www.gadgets360.com/mobiles/reviews/apple-iphone-16e-review-8008088",
        "https://www.gadgets360.com/mobiles/reviews/nothing-phone-3a-review-7943642",
        "https://www.gadgets360.com/mobiles/reviews/oneplus-13-review-7420492",
        "https://www.gadgets360.com/mobiles/reviews/oneplus-nord-ce-4-lite-review-5954674",

        # Add more URLs here
    ]

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in urls:
            try:
                print(f"Scraping: {url}")
                result = await crawler.arun(url=url, config=run_config)

                if result.success:
                    structured_md, metadata = format_for_rag(result.markdown.strip(), result.url)

                    # Save to markdown file
                    with open("clean_reviews.md", "a", encoding="utf-8") as md_file:
                        md_file.write(structured_md)

                    # Save to JSON file
                    json_data = {
                        "url": result.url,
                        "structured_content": structured_md,
                        "metadata": metadata
                    }

                    existing_data = []
                    if os.path.exists("clean_reviews.json"):
                        with open("clean_reviews.json", "r", encoding="utf-8") as json_file:
                            try:
                                existing_data = json.load(json_file)
                            except json.JSONDecodeError:
                                existing_data = []

                    existing_data.append(json_data)

                    with open("clean_reviews.json", "w", encoding="utf-8") as json_file:
                        json.dump(existing_data, json_file, indent=2, ensure_ascii=False)

                    print(f"✅ Successfully processed: {metadata['product_info']['product_name']}")
                    print(f"   Price: {metadata['product_info']['price']}")
                    print(f"   Word Count: {metadata['word_count']}")

                else:
                    print(f"❌ Failed to scrape {url}: {result.error_message}")

            except Exception as e:
                print(f"❌ Error processing {url}: {str(e)}")

    print("\n🎉 Scraping completed!")
    print("📄 Files generated: clean_reviews.md and clean_reviews.json")

if __name__ == "__main__":
    asyncio.run(main())
