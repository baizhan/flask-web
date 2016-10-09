from flask.ext.wtf import Form
from wtforms import SubmitField,StringField,BooleanField,SelectField,PasswordField,TextAreaField
from wtforms.validators import Required,Length,Regexp,Email
from flask.ext.pagedown.fields import PageDownField
from ..models import User,Role


#登录表单
class LoginForm(Form):
    email=StringField('输入Email',validators=[Required(),Length(1,64),Email()])
    password=PasswordField('输入密码',validators=[Required()])
    remenber_me=BooleanField('保持登录')
    submit=SubmitField('登录')
#普通用户的资料编辑表单
class EditProfileForm(Form):
    name=StringField('真实姓名',validators=[Length(0,64)])
    location=StringField('所在城市',validators=[Length(0,64)])
    about_me=TextAreaField('自我介绍')
    submit=SubmitField('提交')

#管理员使用的资料编辑表单
class EditProfileAdminForm(Form):
    email=StringField('邮箱',validators=[Required(),Length(1,64),Email()])
    username=StringField('用户名',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,
                                                                              'Usernames must have only letters,'
                                                                              'numbers,dots or underscores')])
    confirmed=BooleanField('确认')
    role=SelectField('角色',coerce=int)
    name=StringField('真实姓名',validators=[Length(0,64)])
    location=StringField('所在城市',validators=[Length(0,64)])
    about_me=TextAreaField('介绍自己')
    submit=SubmitField('提交')

    def __init__(self,user,*args,**kwargs):
        super(EditProfileAdminForm,self).__init__(*args,**kwargs)
        self.role.choices=[(role.id,role.name) for role in Role.query.order_by(Role.name).all()]
        self.user=user

    def validate_email(self,field):
        if field.data !=self.user.email and User.query.filter_by(email=field.data).first():
            raise  ValidationError('邮箱已经被注册过！')
    def validate_username(self,field):
        if field.data !=self.user.username and User.query.filter_by(username=field.data).first():
            raise  ValidationError('用户名已被使用！')

#博客文章表单
class PostForm(Form):
    title=StringField('标题',validators=[Required()])
    body=TextAreaField('写点什么吧？',validators=[Required()])
    submit=SubmitField('提交')
#文章的评论表单
class CommentForm(Form):
    body=StringField('',validators=[Required()])
    submit=SubmitField('提交')