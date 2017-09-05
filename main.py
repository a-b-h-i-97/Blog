import webapp2
import jinja2
import os

import re
import hashlib
import hmac
from string import letters
import random

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)
SECRET = 'This is a secret string'

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_secure_val(val):
	return '%s|%s' % (val,hmac.new(SECRET,val,hashlib.sha256).hexdigest())

def check_secure_val(secure_val):
	val = secure_val.split('|')[0]
	if(secure_val == make_secure_val(val)):
		return val

class BlogHandler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.out.write(*a,**kw)

	def render_str(self,template,**params):
		t = jinja_env.get_template(template)
		return t.render(**params)

	def render(self,template,**params):
		self.write(self.render_str(template,**params))

	def set_secure_cookie(self,name,val):
		cookie_val = make_secure_val(val)
		self.response.headers.add_header('Set-Cookie','%s=%s;Path=/' % (name,cookie_val))

	def read_secure_cookie(self,name):
		cookie_val = self.request.cookies.get(name)
		return cookie_val and check_secure_val(cookie_val)

	def login(self,user):
		self.set_secure_cookie('user_id',str(user.key().id()))

	def logout(self):
		self.response.headers.add_header('Set-Cookie','user_id=; Path=/')
	
	def initialize(self,*a,**kw):
		webapp2.RequestHandler.initialize(self,*a,**kw)
		uid = self.read_secure_cookie('user_id')
		print(uid)
		self.user = uid and User.by_id(int(uid))





#USER INFORMATION

# def make_salt(length = 5):
# 	return ''.join(random.choice(string.letters) for x in xrange(length))

# def make_pw_hash(name,password,salt = None):
# 	if not salt:
# 		salt = make_salt()

# 	h = hashlib.sha256(name + password + salt).hexdigest()
# 	return '%s|%s' % (h,salt)

def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()

    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s' % (h,salt)

def valid_pw(name,password,h):
	salt = h.split('|')[1]
	return h == make_pw_hash(name,password,salt)


class User(db.Model):
	
	name = db.StringProperty(required = True)
	pw_hash = db.StringProperty(required = True)
	email = db.StringProperty()

	@classmethod
	def by_id(cls,uid):
		return User.get_by_id(uid)

	@classmethod
	def by_name(cls,name):

		user = User.gql("where name = :1", name).get()
		return user

	@classmethod
	def register(cls,name,password,email = None):

		pw_hash = make_pw_hash(name,password)
		return User (name = name,
					 pw_hash = pw_hash,
					 email = email)

	@classmethod
	def login(cls,name,password):

		user = cls.by_name(name)
		if user and valid_pw(name,password,user.pw_hash):
			return user




#BLOG HANDLERS

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)


class Register(BlogHandler):
	def get(self):
		self.render('signup-form.html')

	def post(self):
		self.name = self.request.get('username')
		self.password = self.request.get('password')
		self.verify = self.request.get('verify')
		self.email = self.request.get('email')
		have_error = False


		params = dict(username = self.name,
					  email = self.email)

		if not valid_username(self.name):
			params['error_usernmae'] = "That's not a valid username"
			have_error = True

		if not valid_password(self.password):
			params['error_password'] = "That's not a valid password"
			have_error = True

		elif self.password != self.verify:
			params['error_password'] = "Your passwords did not match"
			have_error = True

		if not valid_email(self.email):
			params['error_email'] = "That's is not a valid email"
			have_error = True

		if have_error:
			self.render('signup-form.html',**params)
		else:

			u = User.by_name(self.name)
			if u:
				msg = "That username is taken, try again."
				params['error_username'] = msg
				self.render('signup-form.html',**params)
	
			else:
				user = User.register(name = self.name,
								 	password = self.password,
								 	email = self.email)
	
				user.put()
				self.login(user)
				self.redirect('/blog/welcome')


class Login(BlogHandler):

	def get(self):
		self.render('login-form.html')

	def post(self):

		username = self.request.get('username')
		password = self.request.get('password')

		user = User.login(username,password)

		if user:
			self.login(user)
			self.redirect('/blog/welcome')
		else:
			error = "Invalid Login"
			self.render('login-form.html',error = error)

class Logout(BlogHandler):

	def get(self):
		self.logout()
		self.redirect('/blog/signup')









class Post(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)

	def render(self):
		self._render_text = self.content.replace('\n','<br>')
		return render_str('post.html', p = self)





class NewPost(BlogHandler):
	def get(self):
		self.render('newpost.html')

	def post(self):
		subject = self.request.get('subject')
		content = self.request.get('content')

		if subject and content:
			p = Post(subject = subject, content = content)
			p.put()
			self.redirect('/blog/%s' % str(p.key().id()))
		else:
			error = 'Enter a valid subject and content'
			self.render('newpost.html',subject = subject, content = content, error = error)


class PostPage(BlogHandler):
	def get(self,post_id):                               #post_id is passed into get because of the paranthesis in handler definition
		key = db.Key.from_path('Post',int(post_id))
		post = db.get(key)

		if not post:
			self.error(404)
			return

		self.render('permalink.html',post = post)

class BlogFront(BlogHandler):
	def get(self):
		posts = db.GqlQuery('Select * from Post order by created desc limit 10')
		self.render('front.html',posts = posts)

class Welcome(BlogHandler):
	def get(self):
		if self.user:
			self.render('welcome.html',username = self.user.name)
		else:
			self.redirect('/blog/signup')



class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!')





app = webapp2.WSGIApplication([('/', MainPage),
    						   ('/blog/?', BlogFront),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/newpost', NewPost),
                               ('/blog/signup', Register),
                               ('/blog/welcome', Welcome),
                               ('/blog/login', Login),
                               ('/blog/logout', Logout),
							   ], 
							  debug=True)
    
