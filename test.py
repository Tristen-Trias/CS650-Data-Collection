import praw
import json
from datetime import datetime, timedelta
import time
import os
import dotenv

def initialize_reddit_client():
    dotenv.load_dotenv()
    
    return praw.Reddit(
        client_id = dotenv.get_key("keys.env", "REDDIT_CLIENT_ID"),
        client_secret = dotenv.get_key("keys.env", "REDDIT_CLIENT_SECRET"),
        user_agent = "CS650 Research Project - CSUSM",
    )

def convert_dates_to_timestamps(start_date, end_date):
    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())
    return start_timestamp, end_timestamp

def is_post_in_date_range(post_timestamp, start_timestamp, end_timestamp):
    return start_timestamp <= post_timestamp <= end_timestamp


def extract_comment_data(comment):
    try:
        return {
            "id": comment.id,
            "author": comment.author.name if comment.author else "[deleted]",
            "body": comment.body,
            "score": comment.score,
            "created_utc": comment.created_utc,
            "is_submitter": comment.is_submitter,
            "parent_id": comment.parent_id,
            "depth": comment.depth if hasattr(comment, 'depth') else 0,
            "gilded": comment.gilded if hasattr(comment, 'gilded') else 0
        }
    except Exception as e:
        print(f"    Error extracting comment data: {e}")
        return None


def collect_post_comments(post, max_comments=None):
    comments_data = []
    
    try:
        post.comments.replace_more(limit=0)
        comment_list = post.comments.list()
        
        if max_comments:
            comment_list = comment_list[:max_comments]
        
        for comment in comment_list:
            if comment.author != "AutoModerator":
                comment_data = extract_comment_data(comment)
                
                if comment_data:
                    comments_data.append(comment_data)
    
    except Exception as e:
        print(f"    Error collecting comments: {e}")
    
    return comments_data


def calculate_engagement_metrics(post):
    try:
        unique_commenters = set()
        for comment in post.comments.list():
            if comment.author != "[deleted]" and comment.author != "AutoModerator" and comment.author:
                unique_commenters.add(comment.author.name)
        
        return {
            "num_comments": post.num_comments,
            "upvote_ratio": post.upvote_ratio,
            "post_status": "removed" if post.removed_by_category else "active",
            "unique_comments": len(unique_commenters),
            "gilded": post.gilded if hasattr(post, 'gilded') else 0,
        }
    except Exception as e:
        print(f"    Error calculating engagement: {e}")
        return {
            "num_comments": post.num_comments,
            "upvote_ratio": post.upvote_ratio,
            "post_status": "unknown",
            "unique_comments": 0,
            "gilded": 0,
        }


def track_outcome_metrics(post):
    try:
        op_name = post.author.name if post.author else ""
        op_comments = []
        
        for comment in post.comments.list():
            if comment.author and comment.author.name == op_name:
                op_comments.append(comment)
        
        op_evidence = False
        for comment in op_comments:
            if any(keyword in comment.body.lower() for keyword in 
                   ["screenshot", "image", "photo", "http", "www.", "pic"]):
                op_evidence = True
                break
        
        thread_solved = False
        if post.link_flair_text:
            thread_solved = any(keyword in post.link_flair_text.lower() 
                              for keyword in ["solved", "resolved", "answered"])
        
        return {
            "final_status": "solved" if thread_solved else "unknown",
            "thread_marked_solved": thread_solved,
            "op_total_comments": len(op_comments),
            "op_evidence": op_evidence,
            "post_edits": bool(post.edited),
            "post_edited_times": post.edited if isinstance(post.edited, (int, float)) else 0,
        }
    except Exception as e:
        print(f"    Error tracking outcomes: {e}")
        return {
            "final_status": "unknown",
            "thread_marked_solved": False,
            "op_total_comments": 0,
            "op_evidence": False,
            "post_edits": False,
            "post_edited_times": 0,
        }


def extract_content_metadata(post):
    try:
        selftext = post.selftext if post.selftext else ""
        
        return {
            "url": post.url,
            "contains_images": any(
                ext in post.url.lower()
                for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]
            ),
            "contains_links": "http" in selftext.lower() or "www." in selftext.lower(),
            "post_length": len(selftext),
            "has_selftext": bool(selftext),
        }
    except Exception as e:
        print(f"    Error extracting content metadata: {e}")
        return {
            "url": post.url if hasattr(post, 'url') else "",
            "contains_images": False,
            "contains_links": False,
            "post_length": 0,
            "has_selftext": False,
        }


def get_post_data(post, keyword, comments_data):
    engagement = calculate_engagement_metrics(post)
    outcome_tracking = track_outcome_metrics(post)
    content_metadata = extract_content_metadata(post)
    
    post_data = {
        "id": post.id,
        "subreddit": post.subreddit.display_name,
        "title": post.title,
        "selftext": post.selftext if post.selftext else "",
        "created_utc": post.created_utc,
        "author": post.author.name if post.author else None,
        "flair": post.link_flair_text,
        "url": post.url,
        "score": post.score,
        "matched_keyword": keyword,
        "permalink": f"https://reddit.com{post.permalink}",
        "engagement": engagement,
        "outcome_tracking": outcome_tracking,
        "content_metadata": content_metadata,
        "comments": comments_data,
        "num_comments_collected": len(comments_data),
    }
    
    return post_data


def search_subreddit_with_keyword(subreddit, keyword, start_timestamp, end_timestamp, 
                                   seen_post_ids, max_posts=100, max_comments=None):
    
    posts_data = []
    
    try:
        search_results = subreddit.search(
            keyword,
            sort='new',
            time_filter='all',
            limit=max_posts
        )
        
        for post in search_results:
            post_timestamp = int(post.created_utc)
            
            if is_post_in_date_range(post_timestamp, start_timestamp, end_timestamp):
                if post.id not in seen_post_ids:
                    seen_post_ids.add(post.id)
                    
                    comments_data = collect_post_comments(post, max_comments)
                    
                    post_data = get_post_data(post, keyword, comments_data)
                    posts_data.append(post_data)
    
    except Exception as e:
        print(f"    Error searching with keyword '{keyword}': {e}")
    
    return posts_data


def search_single_subreddit(reddit, subreddit_name, keywords, start_timestamp, 
                            end_timestamp, seen_post_ids, max_posts_per_search=100,
                            max_comments_per_post=None):
    
    print(f"\n--- Searching r/{subreddit_name} ---")
    subreddit_posts = []
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        
        for keyword in keywords:
            print(f"  Keyword: '{keyword}'")
            
            posts = search_subreddit_with_keyword(
                subreddit, keyword, start_timestamp, end_timestamp,
                seen_post_ids, max_posts_per_search, max_comments_per_post
            )
            
            subreddit_posts.extend(posts)
            print(f"    Found {len(posts)} new posts")
            
            time.sleep(2)  # Rate limiting
    
    except Exception as e:
        print(f"Error accessing r/{subreddit_name}: {e}")
    
    return subreddit_posts


def create_metadata(start_date, end_date, subreddits, keywords, total_posts):
    return {
        "search_date": datetime.now().isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "subreddits": subreddits,
        "keywords": keywords,
        "total_posts_collected": total_posts,
        "total_subreddits_searched": len(subreddits),
        "total_keywords_searched": len(keywords)
    }


def save_to_json(data, output_file):
    try:
        with open(output_file, 'a', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n✓ Saved to: {output_file}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving file: {e}")
        return False


def print_search_summary(total_posts, subreddits, keywords):
    print(f"\n{'='*50}")
    print(f"SEARCH COMPLETE")
    print(f"{'='*50}")
    print(f"✓ Total posts collected: {total_posts}")
    print(f"✓ Subreddits searched: {len(subreddits)}")
    print(f"✓ Keywords used: {len(keywords)}")
    print(f"{'='*50}")


def search_subreddits(subreddits, keywords, start_date, end_date, 
                     max_posts_per_search=100, max_comments_per_post=None):
    print(f"Starting Reddit search...")
    print(f"Subreddits: {', '.join(subreddits)}")
    print(f"Keywords: {len(keywords)}")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    
    reddit = initialize_reddit_client()
    
    start_timestamp, end_timestamp = convert_dates_to_timestamps(start_date, end_date)
    
    seen_post_ids = set()
    
    total_posts_collected = 0

    for subreddit_name in subreddits:
        all_posts = []
        json_file = open(f"data/{subreddit_name}_posts.json", "a", encoding='utf-8')
        
        posts = search_single_subreddit(
            reddit, subreddit_name, keywords, start_timestamp,
            end_timestamp, seen_post_ids, max_posts_per_search,
            max_comments_per_post
        )
        
        all_posts.extend(posts)
        json.dump(all_posts, json_file, indent=4)
        json_file.write("\n")
        json_file.close()
        time.sleep(5) 
        total_posts_collected += len(all_posts)
    
    print_search_summary(total_posts_collected, subreddits, keywords)


if __name__ == "__main__":
    
    if not os.path.exists("data"):
        os.makedirs("data")
    
    for file in os.listdir("data"):
        file_path = os.path.join("data", file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    q1_subreddits = ["malware", "phishing", "scams", "cybersecurity", "jobs", "personalfinance"]
    
    # q2_subreddits = ["cryptocurrency", "relationship_advice", "dating_advice"]
    
    keywords = [
        "is this a scam",
        "is this legit",
        "is this real",
        "sounds like a scam",
        "seems suspicious",
        "too good to be true",
    ]
    
    end = datetime.now()
    start = end - timedelta(days=3*365)
    
    data = search_subreddits(
        subreddits=q1_subreddits,
        keywords=keywords,
        start_date=start,
        end_date=end,
        max_posts_per_search=5000, 
        max_comments_per_post=50
    )