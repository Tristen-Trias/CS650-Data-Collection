import praw
import json
from os import environ as env


def get_reddit_instance():
    return praw.Reddit(
        client_id = "dRTPLiLngNYufDByaLRd1g",
        client_secret = "d7wUe9ZLVewr2dErsU6xWQe0Yp5AyQ",
        user_agent = "CS650 Research Project - CSUSM",
    )

def get_post_data(post):

    engagement = {
        "num_comments": post.num_comments,
        "upvote_ratio": post.upvote_ratio,
        "post_status": "removed" if post.removed_by_category else "active",
        "unique_comments": len(
            {
                comment.author.name
                for comment in post.comments
                if comment.author
            }
        ),
        "gilded": post.gilded,
    }

    outcome_tracking = {
        "final_status": "unknown",
        "thread_marked_solved": False,
        "op_total_comments": len(
            {
                comment
                for comment in post.comments
                if comment.author
                and comment.author.name == (post.author.name if post.author else "")
            }
        ),
        "op_evidence": False,
        "post_edits": post.edited,
        "post_edited_times": (
            post.edited if isinstance(post.edited, int) else 0
        ),
    }

    content_metadata = {
        "url": post.url,
        "contains_images": any(
            ext in post.url.lower()
            for ext in [".jpg", ".jpeg", ".png", ".gif"]
        ),
        "contains_links": "http" in post.selftext.lower()
        or "www." in post.selftext.lower(),
    }

    # Combine all data into a single dictionary
    post_data = {
        "subreddit": post.subreddit.display_name,
        "title": post.title,
        "selftext": post.selftext,
        "created_utc": post.created_utc,
        "author": post.author.name if post.author else None,
        "flair": post.link_flair_text,
        "url": post.url,
        "score": post.score,
        "engagement": engagement,
        "outcome_tracking": outcome_tracking,
        "content_metadata": content_metadata,
    }
                
    return post_data

def search_subreddit(keywords, subreddit, json_file):
    sub_data = {"posts": {}}
    for keyword in keywords:
        print("Searching for keyword:", keyword, "in subreddit:", subreddit.display_name)
        try:
            for post in subreddit.search(keyword, time_filter="day", limit=10):
                print("Processing post:", post.id)
                
                if (hasattr(search_subreddit, "existing_posts") is False):
                    search_subreddit.existing_posts = set()

                data = get_post_data(post)
                print(data)
                
                if sub_data["posts"].get(post.id):
                    print(f"Post {post.id} already exists in data. Skipping.")
                    continue
                else:
                    sub_data.setdefault("posts", {})[post.id] = data

        except Exception as e:
            print(
                f"An error occurred while processing subreddit {subreddit.display_name} with keyword '{keyword}': {e}"
            )
            continue
        
    json.dump(sub_data, json_file, indent=4)
    json_file.write("\n")

def main():
    # Initialize the Reddit instance
    reddit = get_reddit_instance()

    # Find posts with specific keywords across a set of time
    cyber_subreddits = ["malware", "phishing", "scams", "cybersecurity"]
    general_subreddits = ["jobs", "personalfinance"]

    flairs = ["Scam", "Advice", "Help"]

    keywords = [
        "is this a scam",
        "is this legit",
        "is this real",
        "sounds like a scam",
        "seems suspicious",
        "too good to be true",
    ]
    
    for s in cyber_subreddits + general_subreddits:
        with open(f"data//{s}_posts.json", "a") as json_file:
            subreddit = reddit.subreddit(s)
            
            search_subreddit(keywords, subreddit, json_file)

if __name__ == "__main__":
    main()
