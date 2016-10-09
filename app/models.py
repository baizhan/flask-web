from . import db
from werkzeug.security import  generate_password_hash,check_password_hash
from flask.ext.login import UserMixin,AnonymousUserMixin
from . import login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
import hashlib
from datetime import datetime
from flask import request
from markdown import markdown
import bleach
import hashlib
from flask import request
from app.exceptions import ValidationError

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Permission:   #定义权限
    FOLLOW=0b00000001
    COMMENT=0b00000010
    WRITE_ARTICLES=0b00000100
    MODERATE_COMMENTS=0b00001000
    ADMINISTER=0b10000000
#关注关联表的模型实现
class Follow(db.Model):
    __tablename__='follows'
    follower_id=db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    followed_id=db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    timestamp=db.Column(db.DateTime,default=datetime.utcnow)

class Role(db.Model):
    __tablename__='roles'
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(64),unique=True)
    default=db.Column(db.Boolean,default=False,index=True)
    permissions=db.Column(db.Integer)
    users=db.relationship('User',backref='role',lazy='dynamic')
    def __repr__(self):
        return '<Role %r>'%self.name

    @staticmethod
    def insert_roles():
        roles={
            'User':(Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES,True),
            'Administrator':(Permission.FOLLOW |
                                Permission.COMMENT |
                                Permission.WRITE_ARTICLES |
                                Permission.MODERATE_COMMENTS |
                                Permission.ADMINISTER,False)
        }
        for r in roles:
            role=Role.query.filter_by(name=r).first()
            if role is None:
                role=Role(name=r)
            role.permissions=roles[r][0]
            role.default=roles[r][1]
            db.session.add(role)
            db.session.commit()

class User(UserMixin,db.Model):
    __tablename__='users'
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(64),unique=True,index=True)
    username=db.Column(db.String(64),unique=True,index=True)
    password_hash=db.Column(db.String(128))
    role_id=db.Column(db.Integer,db.ForeignKey('roles.id'))
    confirmed=db.Column(db.Boolean,default=False)
    #用户信息字段
    name=db.Column(db.String(64))
    location=db.Column(db.String(64))
    about_me=db.Column(db.Text())
    member_since=db.Column(db.DateTime(),default=datetime.utcnow)
    last_seen=db.Column(db.DateTime(),default=datetime.utcnow)
    #头像
    avatar_hash=db.Column(db.String(32))
    #向post模型添加反向链接
    posts=db.relationship('Post',backref='author',lazy='dynamic')
    #使用两个一对多关系实现多对多关系
    followed=db.relationship('Follow',foreign_keys=[Follow.follower_id],
                             backref=db.backref('follower',lazy='joined',),
                             lazy='dynamic',cascade='all,delete-orphan')
    followers=db.relationship('Follow',foreign_keys=[Follow.followed_id],
                             backref=db.backref('followed',lazy='joined'),
                             lazy='dynamic',cascade='all,delete-orphan')
    #users和评论表之间的一对多关系
    comments=db.relationship('Comment',backref='author',lazy='dynamic')
    #关注
    def follow(self,user):
        if not self.is_following(user):
            f=Follow(follower=self,followed=user)
            db.session.add(f)
            db.session.commit()
    #取消关注
    def unfollow(self,user):
        f=self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
            db.session.commit()
    #正在关注
    def is_following(self,user):
        return self.followed.filter_by(followed_id=user.id).first() is not None
    #被关注
    def is_followed_by(self,user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def generate_confirmation_token(self,expiration=3600):
        s=Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'confirm':self.id})

    def confirm(self,token):
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            data=s.loads(token)
        except:
            return False
        if data.get('confirm') !=self.id:
            return False
        self.confirmed=True
        db.session.add(self)
        return True
    #刷新用户的最后访问时间
    def ping(self):
        self.last_seen=datetime.utcnow()
        db.session.add(self)
        db.session.commit()
    #定义角色
    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email==current_app.config['FLASKY_ADMIN']:
                self.role=Role.query.filter_by(default=False).first()
            if self.role is None:
                self.role=Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash=hashlib.md5(self.email.encode('utf-8')).hexdigest()
        self.follow(self)
    #改变邮箱
    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self,permissions):
        return self.role is not None and (self.role.permissions & permissions)==permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    #定义头像
    def gravatar(self,size=100,default='identicon',rating='g'):
        if request.is_secure:
            url='https://secure.gravatar.com/avatar'
        else:
            url='http://www.gravatar.com/avatar'
        hash=self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url,hash=hash,size=size,default=default,rating=rating)



    #检查密码
    @property
    def password(self):
        raise AttributeError('密码或账户错误！')
    @password.setter
    def password(self,password):
        self.password_hash=generate_password_hash(password)
    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

    #生成虚拟用户
    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u=User(email=forgery_py.internet.email_address(),username=forgery_py.internet.user_name(True),
                   password=forgery_py.lorem_ipsum.word(),confirmed=True,
                   name=forgery_py.name.full_name(),location=forgery_py.address.city(),
                   about_me=forgery_py.lorem_ipsum.sentence(),
                   member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
    #保证自己关注自己
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()
    #关联关注的文章
    @property
    def followed_posts(self):
        return Post.query.join(Follow,Follow.followed_id==Post.author_id).filter(Follow.follower_id==self.id)

    #支持基于令牌的认证
    def generate_auth_token(self,expiration):
        s=Serializer(current_app.config['SECRET_KEY'],expires_in=expiration)
        return s.dumps({'id':self.id})
    @staticmethod
    def verify_auth_token(token):
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            data=s.loads(token)
        except:
            return None
        return User.query.get(data['id'])
    #把用户转换成json格式的序列号字典
    def to_json(self):
        json_user={
            'url':url_for('api.get_post',id=self.id,_external=True),
            'username':self.username,
            'member_since':self.member_since,
            'last_seen':self.last_seen,
            'posts':url_for('api_get_user_posts',id=self.id,_external=True),
            'followed_posts':url_for('api.get_user_followed_posts',id=self.id,_external=True),
            'post_count':self.posts.count()
        }
        return json_user

class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False
    def is_administrator(self):
        return False
login_manager.anonymous_user=AnonymousUser

#定义文章模型
class Post(db.Model):
    __tablename__='posts'
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.Text)
    body=db.Column(db.Text)
    timestamp=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    author_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    comments=db.relationship('Comment',backref='post',lazy='dynamic')

    #生成虚拟文章
    @staticmethod
    def generate_fake(count=100):
        from random import seed,randint
        import forgery_py

        seed()
        user_count=User.query.count()
        for i in range(count):
            u=User.query.offset(randint(0,user_count-1)).first()
            p=Post(title=forgery_py.lorem_ipsum.sentence(randint(1)),body=forgery_py.lorem_ipsum.sentence(randint(1,3)),
                   timestamp=forgery_py.date.date(True),author=u)
            db.session.add(p)
            db.session.commit()
    # 把文章 转换成json格式的格式化字典
    def to_json(self):
        json_post={
            'url':url_for('api.get_post',id=self.id,_external=True),
            'title':self.title,
            'body':self.body,
            'timestamp':self.timestamp,
            'author':url_for('api.get_user',id=self.author_id,_external=True),
            'comments':url_for('api.get_post_comments',id=self.id,_external=True),
            'comment_count':self.comments.count()
        }
        return json_post

    #从JSON格式数据创建一篇博客文章
    @staticmethod
    def from_json(json_post):
        title=json_post.get('title')
        body=json_post.get('body')
        if body is None or body=='' and title is None or title=='':
            raise ValidationError('文章没有标题或内容')
        return Post(title=title,body=body)
#定义评论模型
class Comment(db.Model):
    __tablename__='comments'
    id=db.Column(db.Integer,primary_key=True)
    body=db.Column(db.Text)
    timestamp=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    disabled=db.Column(db.Boolean)
    author_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id=db.Column(db.Integer,db.ForeignKey('posts.id'))

    #转换为json格式
    def to_json(self):
        json_comment={
            'url':url_for(api.get_comment,id=self.id,_external=True),
            'post':url_for(api.get_post,id=self.post_id,_external=True),
            'body':self.body,
            'timestamp':self.timestamp,
            'author':url_for(api.get_user,id=self.author_id,_external=True)
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body=json_comment.get('body')
        if body is None or body=='':
            raise ValidationError('评论没有内容')
        return Comment(body=body)



