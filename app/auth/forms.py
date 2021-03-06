from flask.ext.wtf import Form
from wtforms import StringField,PasswordField,BooleanField,SubmitField
from wtforms.validators import Required,Length,Email,Regexp,EqualTo
from wtforms import ValidationError
from ..models import  User



class RegistrationForm(Form):
    email=StringField('邮箱',validators=[Required(),Length(1,64),Email()])
    username=StringField('用户名',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,
                                                                               'Usernames must have only letters,'
                                                                               'numbers,dots or underscores')])
    password=PasswordField('密码',validators=[Required(),EqualTo('password2',message='Passwords must match.')])
    password2=PasswordField('确认密码',validators=[Required()])
    submit=SubmitField('注册')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已经被注册过！')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已经存在。')
        
