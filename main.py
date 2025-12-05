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

def get_post_data(post, keyword, comments_data):
    
    post_data = {
        "id": post.id,
        "title": post.title,
        "body": post.selftext if post.selftext else "",
        "post_created_utc": post.created_utc,
        "post_year": datetime.fromtimestamp(post.created_utc).year,
        "post_month": datetime.fromtimestamp(post.created_utc).month,
        "post_day": datetime.fromtimestamp(post.created_utc).day,
        "post_hour": datetime.fromtimestamp(post.created_utc).hour,
        "post_day_of_week": datetime.fromtimestamp(post.created_utc).strftime("%A"),
        "upvotes": post.score,
        "num_comments": post.num_comments,
        "url": post.url,
        "selfPost": post.is_self,        
        "author": post.author.name if post.author else None,
        "permalink": post.permalink,
        "flair": post.link_flair_text,
        "domain": post.domain,
        "guilded": post.gilded if hasattr(post, 'gilded') else 0,
        "total_awards": post.total_awards_received,
        "post_distinguished": post.distinguished,
        "edited": post.edited,
        "archived": post.archived,
        "locked": post.locked,
        "removed": post.removed_by_category if post.removed_by_category else None,
        "thumbnail": post.thumbnail if post.thumbnail else None,
    }
    
    # add comments data
    post_data["comments"] = comments_data
    
    return post_data
    
def gather_all_posts_in_daterange(subreddit_name, start_timestamp, 
                                   end_timestamp, max_posts=1000, divide_num=100,
                                   max_comments_per_post=None, sort_by='new'):
    
    print(f"\n--- Gathering all posts from r/{subreddit_name} ---")
    print(f"    Date range: {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
    
    reddit = initialize_reddit_client()
    
    all_posts = []
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        
        # Choose the appropriate listing method
        if sort_by == 'new':
            listing = subreddit.new(limit=max_posts)
        elif sort_by == 'hot':
            listing = subreddit.hot(limit=max_posts)
        elif sort_by == 'top':
            listing = subreddit.top(time_filter='all', limit=max_posts)
        elif sort_by == 'controversial':
            listing = subreddit.controversial(time_filter='all', limit=max_posts)
        else:
            listing = subreddit.new(limit=max_posts)
        
        posts_in_range = 0
        posts_checked = 0
        # json_num_check = 0
        # numFiles = 1
        
        for post in listing:
            posts_checked += 1
            post_timestamp = int(post.created_utc)
            
            # Check if post is within date range
            if is_post_in_date_range(post_timestamp, start_timestamp, end_timestamp):
                # Collect comments
                comments_data = collect_post_comments(post, max_comments_per_post)
                
                # Extract post data with all metrics (no keyword needed)
                post_data = get_post_data(post, keyword="all_posts", comments_data=comments_data)
                all_posts.append(post_data)
                posts_in_range += 1
                # json_num_check += 1
                
                if posts_in_range % 100 == 0:
                    print(f"    Collected {posts_in_range} posts so far...")
            
            # Early exit if we're past the date range (only works with 'new' sort)
            elif sort_by == 'new' and post_timestamp < start_timestamp:
                print(f"    Reached posts before start date, stopping search")
                break
            
            # if json_num_check >= divide_num:
            #     json_file = open(f"data/{subreddit_name}_all_posts{numFiles}.json", "a", encoding='utf-8')
            #     json.dump(all_posts, json_file, indent=4)
            #     json_file.write("\n")
            #     json_file.close()
            #     json_num_check = 0
            #     numFiles += 1
            #     print(f"    ✓ Saved {len(all_posts)} posts to JSON so far.")
            #     all_posts = []
        
        print(f"    ✓ Total posts checked: {posts_checked}")
        print(f"    ✓ Posts in date range: {len(all_posts)}")
    
    except Exception as e:
        print(f"Error accessing r/{subreddit_name}: {e}")
        
    json_file = open(f"data/{subreddit_name}_all_posts.json", "a", encoding='utf-8')
    json.dump(all_posts, json_file, indent=4)
    json_file.write("\n")
    json_file.close()
    time.sleep(5) 
    
    return all_posts


if __name__ == "__main__":
    
    if not os.path.exists("data"):
        os.makedirs("data")
    
    for file in os.listdir("data"):
        file_path = os.path.join("data", file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # Define date range: last 15 years from 31-Oct-2025 to 1-Jan-2011    
    start = datetime(2011, 1, 1)
    # end = datetime(2025, 10, 31)
    end = datetime.now()
    
    data = gather_all_posts_in_daterange(
        subreddit_name="phishing",
        start_timestamp=int(start.timestamp()),
        end_timestamp=int(end.timestamp()),
        max_posts=100000,
        max_comments_per_post=50,
        sort_by='new',
        divide_num=200
    )