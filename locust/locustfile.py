from locust import HttpUser, task, between, tag, SequentialTaskSet
from locust.exception import StopUser
import random
import string

# --- Helper Functions ---
def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_placeholder_image():
    # 1x1 Pixel Black Transparent GIF (Smallest valid image)
    return "data:image/gif;base64,R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs="

def register_and_login(user):
    user.username = f"user_{random_string()}@test.com"
    user.password = "password123"
    
    # Register
    with user.client.post("/api/auth/register", json={"username": user.username, "password": user.password}, catch_response=True, name="/api/auth/register") as response:
        if response.status_code != 200:
            # It's possible the user already exists (rare with random string), or server error
            if response.status_code != 400: # 400 might mean 'user exists' which is fine to proceed to login
                 response.failure(f"Registration failed: {response.text}")
                 return False

    # Login
    with user.client.post("/api/auth/login", json={"username": user.username, "password": user.password}, catch_response=True, name="/api/auth/login") as response:
        if response.status_code == 200:
            token = response.json().get("accessToken")
            if token:
                user.client.headers.update({"Authorization": f"Bearer {token}"})
                
                # Submit Interest Form (Required for new users)
                interest_payload = {
                    "name": f"User_{random_string(4)}",
                    "surname": f"Surname_{random_string(4)}",
                    "dateOfBirth": "1995-05-15",
                    "height": random.randint(160, 190),
                    "weight": round(random.uniform(55.0, 90.0), 1),
                    "gender": random.choice(["Male", "Female"]),
                    "profilePhoto": get_placeholder_image() # Sending a valid Base64 image
                }
                
                with user.client.post("/api/interest-form/submit", json=interest_payload, catch_response=True, name="/api/interest-form/submit") as form_response:
                    if form_response.status_code != 200:
                        form_response.failure(f"Interest Form submission failed: {form_response.text}")
                        return False
                
                return True
        else:
            response.failure(f"Login failed: {response.text}")
            return False

# --- Standard User Classes ---

class PublicUser(HttpUser):
    """
    Simulates unauthenticated traffic.
    Focus: Network, LoadBalancer, Auth Service resilience.
    """
    wait_time = between(1, 3)

    @tag('public', 'db_read')
    @task(3)
    def check_email_exists(self):
        email = f"test_{random_string()}@example.com"
        self.client.get(f"/api/auth/exists?email={email}", name="/api/auth/exists [Public Read]")

    @tag('public', 'auth_fail')
    @task(1)
    def attempt_bad_login(self):
        # Intentionally failing login to test error handling/logging overhead
        bad_creds = {"username": "nonexistent_user", "password": "wrongpassword"}
        with self.client.post("/api/auth/login", json=bad_creds, catch_response=True, name="/api/auth/login [Bad Creds]") as response:
            if response.status_code == 401 or response.status_code == 403 or response.status_code == 400:
                response.success()
            else:
                # If it lets us in or errors out 500, that's a failure
                response.failure(f"Bad login expected 4xx, got {response.status_code}")

class AuthenticatedUser(HttpUser):
    """
    Simulates standard authenticated behavior.
    Focus: Auth (CPU), General Reads/Writes, API Logic.
    """
    wait_time = between(2, 5)
    
    def on_start(self):
        if not register_and_login(self):
            raise StopUser()  # Stop user if registration/login fails

    @tag('read', 'db_read_complex')
    @task(3)
    def check_homepage_feed(self):
        with self.client.get("/api/recipe/get-all", catch_response=True, name="/api/recipe/get-all [Complex Read]") as response:
            if response.status_code != 200:
                response.failure(f"Failed to get recipes: {response.status_code}")

    @tag('read', 'db_read_single')
    @task(2)
    def view_random_recipe_details(self):
        # First get a list to find an ID (simulating user browsing)
        with self.client.get("/api/recipe/get-all", catch_response=True, name="/api/recipe/get-all [Setup]") as response:
            if response.status_code == 200:
                try:
                    recipes = response.json()
                    if recipes:
                        target = random.choice(recipes)
                        # Nested with-block for the second request
                        with self.client.get(f"/api/recipe/get?recipeId={target['id']}", catch_response=True, name="/api/recipe/get [Single Read]") as detail_response:
                             if detail_response.status_code != 200:
                                 detail_response.failure(f"Failed to get recipe details: {detail_response.status_code}")
                except Exception as e:
                    response.failure(f"Failed to parse JSON: {e}")
            else:
                 response.failure(f"Failed to get recipe list: {response.status_code}")

    @tag('write', 'db_write')
    @task(1)
    def create_recipe(self):
        payload = {
            "title": f"Recipe {random_string()}",
            "instructions": ["Mix ingredients", "Bake at 350F", "Serve warm"],
            "ingredients": [
                {"name": "Flour", "amount": 200, "unit": "g"},
                {"name": "Sugar", "amount": 100, "unit": "g"}
            ],
            "tag": "Test",
            "type": random.choice(["Lunch", "Dinner", "Dessert"]),
            "photo": get_placeholder_image(),
            "totalCalorie": random.randint(100, 800),
            "price": round(random.uniform(5.0, 50.0), 2)
        }
        with self.client.post("/api/recipe/create", json=payload, catch_response=True, name="/api/recipe/create [DB Write]") as response:
            if response.status_code != 200:
                response.failure(f"Failed to create recipe: {response.status_code}")

class SocialUser(HttpUser):
    """
    Simulates social interactions.
    Focus: High concurrency DB updates (Locking), Foreign Key checks.
    """
    wait_time = between(1, 3)
    feed_ids = []

    def on_start(self):
        if not register_and_login(self):
            raise StopUser()  # Stop user if registration/login fails
        # Fetch recent feeds to populate local cache of IDs
        self.refresh_feeds()
            
    def refresh_feeds(self):
        with self.client.get("/api/feeds/recent?pageNumber=0", catch_response=True, name="/api/feeds/recent [Setup]") as response:
            if response.status_code == 200:
                try:
                    feeds = response.json()
                    # Extract IDs safely
                    self.feed_ids = [f['id'] for f in feeds if isinstance(f, dict) and 'id' in f]
                    
                    # Fallback if empty
                    if not self.feed_ids:
                        self.create_fallback_feed()
                except:
                    pass

    def create_fallback_feed(self):
        payload = {
            "title": f"Fallback Recipe {random_string()}",
            "instructions": ["Step 1"],
            "ingredients": [],
            "tag": "Fallback",
            "type": "Dinner",
            "photo": "",
            "totalCalorie": 500,
            "price": 10.0
        }
        self.client.post("/api/recipe/create", json=payload, name="/api/recipe/create [Fallback]")
        # Try fetching again briefly
        response = self.client.get("/api/feeds/recent?pageNumber=0", name="/api/feeds/recent [Retry]")
        if response.status_code == 200:
             feeds = response.json()
             self.feed_ids = [f['id'] for f in feeds if isinstance(f, dict) and 'id' in f]

    @tag('social', 'db_lock')
    @task(4)
    def like_feed(self):
        if not self.feed_ids: 
            self.refresh_feeds()
            if not self.feed_ids: return

        feed_id = random.choice(self.feed_ids)
        with self.client.post("/api/feeds/like", json={"feedId": feed_id}, catch_response=True, name="/api/feeds/like [DB Update]") as response:
             if response.status_code != 200:
                 response.failure(f"Failed to like feed: {response.status_code}")

    @tag('social', 'db_write')
    @task(2)
    def comment_feed(self):
        if not self.feed_ids: 
            self.refresh_feeds()
            if not self.feed_ids: return

        feed_id = random.choice(self.feed_ids)
        msg = random.choice(["Great!", "Yummy!", "Nice photo", "Will try this"])
        with self.client.post("/api/feeds/comment", json={"feedId": feed_id, "message": msg}, catch_response=True, name="/api/feeds/comment [DB Write]") as response:
             if response.status_code != 200:
                 response.failure(f"Failed to comment: {response.status_code}")

    @tag('social', 'db_read')
    @task(1)
    def view_feed_comments(self):
        if not self.feed_ids: return
        # Assuming there is an endpoint to view details/comments, typically getting the feed again or a specific comments endpoint
        # If no specific comments endpoint, we re-fetch the feed which likely joins comments
        feed_id = random.choice(self.feed_ids)
        # Note: Adjust endpoint if a specific /comments endpoint exists. 
        # For now, we assume getting the recipe/feed details loads comments.
        # Check backend: usually /api/recipe/get?recipeId=... or similar
        with self.client.get(f"/api/recipe/get?recipeId={feed_id}", catch_response=True, name="/api/recipe/get [Social Read]") as response:
             if response.status_code != 200:
                 response.failure(f"Failed to view comments: {response.status_code}")


class JourneyTaskSet(SequentialTaskSet):
    """
    Defines a strict order of operations for a user journey.
    """
    @task
    def browse_feeds(self):
        with self.client.get("/api/recipe/get-all", catch_response=True, name="/api/recipe/get-all [Journey]") as response:
            if response.status_code == 200:
                recipes = response.json()
                if recipes:
                    self.parent.target_recipe_id = recipes[0]['id']

    @task
    def view_details(self):
        if hasattr(self.parent, 'target_recipe_id'):
            with self.client.get(f"/api/recipe/get?recipeId={self.parent.target_recipe_id}", catch_response=True, name="/api/recipe/get [Journey]") as response:
                 pass

    @task
    def save_recipe(self):
        if hasattr(self.parent, 'target_recipe_id'):
            with self.client.post("/api/saved-recipes/save", json={"recipeId": self.parent.target_recipe_id}, catch_response=True, name="/api/saved-recipes/save [Journey]") as response:
                 pass

    @task
    def view_my_saved_recipes(self):
        with self.client.get("/api/saved-recipes/get-all", catch_response=True, name="/api/saved-recipes/get-all [Journey]") as response:
             pass

class JourneyUser(HttpUser):
    """
    Simulates a full user flow: Browse -> View -> Save -> View Saved.
    Focus: End-to-end latency and system cohesion.
    """
    wait_time = between(2, 5)
    tasks = [JourneyTaskSet]
    
    def on_start(self):
        if not register_and_login(self):
            raise StopUser()  # Stop user if registration/login fails
