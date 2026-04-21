from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DateField,
                     SelectField, SubmitField)
from wtforms.validators import DataRequired, Optional


class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    assign_to = SelectField('Assign To', choices=[
        ('class', 'Entire Class'), ('student', 'Specific Student')
    ])
    class_id = SelectField('Class', coerce=int, validators=[Optional()])
    student_id = SelectField('Student', coerce=int, validators=[Optional()])
    submit = SubmitField('Create Task')


class TaskReviewForm(FlaskForm):
    status = SelectField('Decision', choices=[
        ('approved', 'Approve'), ('rejected', 'Reject')
    ])
    review_comment = TextAreaField('Comment', validators=[Optional()])
    submit = SubmitField('Submit Review')
