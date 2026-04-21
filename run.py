import click
from app import create_app, db
from app.models import User

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}


@app.cli.command('create-admin')
@click.argument('name')
@click.argument('email')
@click.argument('password')
def create_admin(name, email, password):
    """Create the first admin user: flask create-admin "Name" email password"""
    with app.app_context():
        if User.query.filter_by(email=email).first():
            click.echo('Error: Email already exists.')
            return
        admin = User(name=name, email=email, role='admin', is_active=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f'Admin "{name}" created successfully.')


@app.cli.command('init-db')
def init_db():
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        click.echo('Database tables created.')


if __name__ == '__main__':
    app.run(debug=True, port=8001)
