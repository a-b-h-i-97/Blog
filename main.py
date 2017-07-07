import webapp2
import jinja2
import os

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogHandler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.out.write(*a,**kw)

	def render_str(self,template,**params):
		t = jinja_env.get_template(template)
		return t.render(**params)

	def render(self,template,**params):
		self.write(self.render_str(template,**params))

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
	def get(self,post_id):
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







class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!')





app = webapp2.WSGIApplication([('/', MainPage),
    						   ('/blog/?', BlogFront),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/newpost', NewPost),
							   ], 
							  debug=True)
    
