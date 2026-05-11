from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import Length, EqualTo, Email, DataRequired, ValidationError

class RegisterForm(FlaskForm):
    # Account Information
    username = StringField(label='Username', validators=[Length(min=2, max=30), DataRequired()])
    email_address = StringField(label='Email Address', validators=[Email(), DataRequired()])
    role = SelectField(label='Account Type', choices=[('consumer', 'Consumer'), ('seller', 'Seller')], validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[Length(min=6), DataRequired()])
    password_confirm = PasswordField(label='Confirm Password', validators=[EqualTo('password'), DataRequired()])
    
    # Personal & Shipping Information
    full_name = StringField(label='Full Name', validators=[Length(min=2, max=50), DataRequired()])
    phone_number = StringField(label='Phone Number', validators=[Length(min=10, max=15), DataRequired()])
    address = StringField(label='Address', validators=[Length(min=5, max=100), DataRequired()])
    city = StringField(label='City', validators=[Length(min=2, max=50), DataRequired()])
    state = StringField(label='State', validators=[Length(min=2, max=50), DataRequired()])
    zip_code = StringField(label='ZIP Code', validators=[Length(min=5, max=10), DataRequired()])
    
    submit = SubmitField(label='Create Account')

class LoginForm(FlaskForm):
    username = StringField(label='User Name:', validators=[DataRequired()])
    password = PasswordField(label='Password:', validators=[DataRequired()])
    submit = SubmitField(label='Sign In')
