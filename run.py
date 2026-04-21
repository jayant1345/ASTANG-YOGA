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


@app.cli.command('seed-classes')
def seed_classes():
    """Seed the 9 default yoga batch classes (skips if already present)."""
    from app.models import YogaClass
    with app.app_context():
        if YogaClass.query.first():
            click.echo('Classes already exist — skipping seed.')
            return
        classes = [
            ('Morning 06:15 Batch', '06:15 AM', 'Main Hall', 2500.0),
            ('Morning 07:15 Batch', '07:15 AM', 'Main Hall', 2500.0),
            ('Morning 08:15 Batch', '08:15 AM', 'Main Hall', 2500.0),
            ('Morning 09:15 Batch', '09:15 AM', 'Main Hall', 2500.0),
            ('Morning 10:15 Batch', '10:15 AM', 'Main Hall', 2500.0),
            ('Morning 11:15 Batch', '11:15 AM', 'Main Hall', 2500.0),
            ('Evening 05:15 Batch', '05:15 PM', 'Main Hall', 2500.0),
            ('Evening 06:15 Batch', '06:15 PM', 'Main Hall', 2500.0),
            ('Evening 07:15 Batch', '07:15 PM', 'Main Hall', 2500.0),
        ]
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            click.echo('No admin user found — run create-admin or set ADMIN_EMAIL/ADMIN_PASSWORD first.')
            return
        for name, time, location, fee in classes:
            db.session.add(YogaClass(
                name=name,
                schedule_time=time,
                location=location,
                monthly_fee_amount=fee,
                instructor_id=admin.id,
            ))
        db.session.commit()
        click.echo(f'Seeded {len(classes)} yoga classes.')


if __name__ == '__main__':
    app.run(debug=True, port=8001)
