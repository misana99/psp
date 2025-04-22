from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def greet_user(username):
    return f"HELLO! {username}. you've successful sign in."


def signin(req):
    if req.method == 'POST':
        username = req.POST['username']
        password = req.POST['password']
        
        # Authenticate user
        user = authenticate(req, username=username, password=password)
        
        if user is not None:
            login(req, user)

            # Redirect based on group
            if user.groups.filter(name='Staff').exists():
                messages.success(req, greet_user(user.username))
                req.session["user_group"] = "Staff"
                return redirect('pspn:dash')
            elif user.groups.filter(name='Student').exists():
                messages.success(req, greet_user(user.username))
                req.session["user_group"] = "Student"
                return redirect('pspn:home')
            else:
                return redirect('signin')
        else:
            messages.error(req, "Invalid credentials")
            return redirect('signin')
    return render(req, 'index.html')

# Logout View
def logout_view(req):
    logout(req)
    req.session.flush()
    messages.success(req, "You've logged out successful")
    return redirect('signin')