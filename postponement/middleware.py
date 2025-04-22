from django.utils.timezone import now
from django.conf import settings
from django.contrib.auth import logout
import datetime
from django.contrib import messages

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, req):
        if req.user.is_authenticated:
            last_activity = req.session.get('last_activity')
            
            if last_activity:
                # Convert string back to datetime
                last_activity = datetime.datetime.fromisoformat(last_activity)
                inactive_time = (now() - last_activity).total_seconds()
                
                if inactive_time > settings.SESSION_COOKIE_AGE:
                    logout(req)
                    req.session.flush()  # Clear session
            
            # Store datetime as a string
            req.session['last_activity'] = now().isoformat()
        
        return self.get_response(req)
