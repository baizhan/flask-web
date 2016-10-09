from flask import render_template,redirect,request,url_for,flash
from ..email import send_email
from . import auth
from .forms import RegistrationForm
from ..models import User,Post
from .. import db
from flask.ext.login import logout_user,login_required,current_user,login_user


#注册
@auth.route('/register/',methods=['GET','POST'])
def register():
    form=RegistrationForm()
    if form.validate_on_submit():
        user=User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        token=user.generate_confirmation_token()
        send_email(user.email,'请确认您的邮箱地址','auth/email/confirm',user=user,token=token)
        flash('确认邮箱的邮件已发往您的邮箱，请您及时确认！')
        return redirect(url_for('main.user',username=user.username))
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(page, per_page=10, error_out=False)
    posts = pagination.items
    return render_template('auth/register.html',form=form,posts=posts,pagination=pagination)
#退出
@auth.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('您已经成功退出了！')
    return redirect(url_for('main.index'))
#确认邮箱
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('您已经确认过邮箱了！谢谢！')
    else:
        flash('链接失效或已过期！')
    return redirect(url_for('main.index'))

#过滤未确认的账户
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] !='auth.' \
                and request.endpoint !='static':
            return redirect(url_for('auth.unconfirmed'))
@auth.route('/unconfirmed/')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

#重新发送账户确认邮件
@auth.route('/confirm/')
@login_required
def resend_confirmation():
    token=current_user.generate_confirmation_token()
    send_email(current_user.email,'确认您的账户','auth/email/confirm',user=current_user,token=token)
    flash('一封确认邮件已经发送到您的邮箱,请您点击确认')
    return redirect(url_for('main.index'))
