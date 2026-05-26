from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProductForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    stock_quantity = IntegerField('Initial Stock', validators=[DataRequired()])
    submit = SubmitField('Save Product')

class CustomerForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    submit = SubmitField('Save Customer')

class SaleForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    payment_type = SelectField('Payment Method', choices=[('Cash', 'Cash'), ('Paytm', 'Paytm'), ('UPI', 'UPI'), ('Card', 'Card'), ('Net Banking', 'Net Banking'), ('Other', 'Other')], validators=[DataRequired()])
    submit = SubmitField('Record Sale')

class InventoryForm(FlaskForm):
    stock_level = IntegerField('Stock Level', validators=[DataRequired()])
    restock_threshold = IntegerField('Restock Threshold', validators=[DataRequired()])
    submit = SubmitField('Update Inventory')
