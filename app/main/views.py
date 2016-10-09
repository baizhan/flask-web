from flask.ext.login import login_user,login_required,current_user
from flask import session,redirect,url_for,render_template,flash,make_response
from .forms import LoginForm,EditProfileForm,EditProfileAdminForm,PostForm,CommentForm
from  . import main
from ..models import User,Role,Permission,Post,Comment
from flask import request
from flask import abort
from ..decorators import admin_required,permission_required
from .. import db
from datetime import datetime
#首页路由+处理文章
@main.route('/',methods=['GET','POST'])
def index():
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user,form.remenber_me.data)
            return redirect(request.args.get('next') or url_for('main.user',username=user.username,user=user))
        flash('密码或账户错误。')
    page=request.args.get('page',1,type=int)
    pagination=Post.query.order_by(Post.timestamp.desc()).paginate(page,per_page=10,error_out=False)
    posts=pagination.items
    return render_template('index1.html',form=form,posts=posts,pagination=pagination)

#用户页面的路由
@main.route('/user/<username>',methods=['GET','POST'])
def user(username):
    user=User.query.filter_by(username=username).first()
    form=PostForm()
    if user is None:
        abort(404)
    if user==current_user and form.validate_on_submit():
        post=Post(title=form.title.data,body=form.body.data,author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
    show_followed=True
    if current_user.is_authenticated:
        show_followed=bool(request.cookies.get('show_followed',''))
    if show_followed:
        query=user.followed_posts
    else:
        query=Post.query
    form.title.data=''
    form.body.data=''
    page=request.args.get('page',1,type=int)
    pagination=query.order_by(Post.timestamp.desc()).paginate(page,per_page=10,error_out=False)
    posts=pagination.items
    return render_template('user.html',user=user,form=form,posts=posts,pagination=pagination,show_followed=show_followed)

#普通用户编辑资料路由
@main.route('/edit-profile/',methods=['GET','POST'])
@login_required
def edit_profile():
    form=EditProfileForm()
    if form.validate_on_submit():
        current_user.name=form.name.data
        current_user.location=form.location.data
        current_user.about_me=form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash('您的资料已成功更新！')
        return redirect(url_for('.user',username=current_user.username))
    form.name.data=current_user.name
    form.location.data=current_user.location
    form.about_me.data=current_user.about_me
    return render_template('edit_profile.html',form=form,user=current_user)

#管理员的资料编辑路由
@main.route('/edit-profile/<int:id>/',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user=User.query.get_or_404(id)
    form=EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email=form.email.data
        user.username=form.username.data
        user.confirmed=form.confirmed.data
        user.role=Role.query.get(form.role.data)
        user.name=form.name.data
        user.location=form.location.data
        user.about_me=form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('资料已经成功更新！')
        return redirect(url_for('main.user',username=user.username))
    form.email.data=user.email
    form.username.data=user.username
    form.confirmed.data=user.confirmed
    form.role.data=user.role_id
    form.name.data=user.name
    form.location.data=user.location
    form.about_me.data=user.about_me
    return render_template('edit_profile.html',form=form,user=user)
#编辑文章
@main.route('/edit_post/<int:id>',methods=['POST','GET'])
@login_required
def edit_post(id):
    post=Post.query.get_or_404(id)
    if current_user !=post.author:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title=form.title.data
        post.body=form.body.data
        post.timestamp=datetime.utcnow()
        db.session.add(post)
        db.session.commit()
        flash('您的文章已经修改成功')
        return redirect(url_for('main.user',username=current_user.username))
    form.title.data=post.title
    form.body.data=post.body
    return render_template('edit_post.html',form=form)

#删除文章
@main.route('/delete_post/<int:id>',methods=['GET','POST'])
@login_required
def delete_post(id):
    post=Post.query.get_or_404(id)
    if current_user==post.author:
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('main.user',username=current_user.username))
#“关注”的路由和视图函数
@main.route('/follow/<username>/')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.user',username=current_user.username))
    if current_user.is_following(user):
        flash('您已经关注了该用户')
        return redirect(url_for('main.user',username=username))
    current_user.follow(user)
    flash('您现在关注了%s'% username)
    return redirect(url_for('main.user',username=username))
#“取消关注”的路由和视图函数
@main.route('/unfollow/<username>/')
@login_required
def unfollow(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.user',username=current_user.username))
    if  not current_user.is_following(user):
        flash('您已经取消关注了该用户')
        return redirect(url_for('main.user',username=username))
    current_user.unfollow(user)
    flash('您现在已经取消关注了%s'% username)
    return redirect(url_for('main.user',username=username))

#“粉丝”的路由和视图函数
@main.route('/followers/<username>/')
def followers(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.index',username=current_user.username))
    page=request.args.get('page',1,type=int)
    pagination=user.followers.paginate(page,per_page=10,error_out=False)
    follows=[{'user':item.follower,'timestamp':item.timestamp} for item in pagination.items]
    return render_template('followers.html',user=user,endpoint='main.followers',
                            pagination=pagination,follows=follows)
#“关注者”的路由和视图函数
@main.route('/followed/<username>/')
def followed_by(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.index',username=current_user.username))
    page=request.args.get('page',1,type=int)
    pagination=user.followed.paginate(page,per_page=10,error_out=False)
    follows=[{'user':item.followed,'timestamp':item.timestamp} for item in pagination.items]
    return render_template('followed.html',user=user,endpoint='main.followed_by',
                            pagination=pagination,follows=follows)
#查看所有文章
@main.route('/all/')
@login_required
def show_all():
    resp=make_response(redirect(url_for('main.user',username=current_user.username)))
    resp.set_cookie('show_followed','',max_age=30*24*60*60)
    return resp
#查看所关注的文章
@main.route('/followed/')
@login_required
def show_followed():
    resp=make_response(redirect(url_for('main.user',username=current_user.username)))
    resp.set_cookie('show_followed','1',max_age=30*24*60*60)
    return resp
#文章的固定链接
@main.route('/post/<int:id>/',methods=['GET','POST'])
def post(id):
    post=Post.query.get_or_404(id)
    form=CommentForm()
    if form.validate_on_submit():
        comment=Comment(body=form.body.data,post=post,author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('您的评论已成功提交！')
        return redirect(url_for('main.post',id=post.id,page=-1))
    page=request.args.get('page',1,type=int)
    if page==-1:
        page=(post.comments.count()-1)/10+1
    pagination=post.comments.order_by(Comment.timestamp.asc()).paginate(page,per_page=10,error_out=False)
    comments=pagination.items
    return render_template('post.html',post=post,form=form,comments=comments,pagination=pagination)
#管理评论的路由
@main.route('/modetate/')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page=request.args.get('page',1,type=int)
    pagination=Comment.query.order_by(Comment.timestamp.desc()).paginate(page,per_page=10,error_out=False)
    comments=pagination.items
    return render_template('moderate.html',comments=comments,pagination=pagination,page=page)
#评论管理路由
@main.route('/moderate/enable/<int:id>/')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment=Comment.query.get_or_404(id)
    comment.disabled=False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate',page=request.args.get('page',i,type=int)))
@main.route('/moderate/disable/<int:id>/')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment=Comment.query.get_or_404(id)
    comment.disabled=True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate',page=request.args.get('page',1,type=int)))
