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
    """Create tables, auto-create admin, deduplicate and seed classes."""
    from app import _auto_create_admin
    from app.models import YogaClass
    from sqlalchemy import func
    with app.app_context():
        db.create_all()
        click.echo('Tables ready.')

        _auto_create_admin()

        # Remove duplicate classes — keep lowest id per name
        name_to_min_id = dict(
            db.session.query(YogaClass.name, func.min(YogaClass.id))
            .group_by(YogaClass.name).all()
        )
        if name_to_min_id:
            keep_ids = list(name_to_min_id.values())
            removed = YogaClass.query.filter(YogaClass.id.notin_(keep_ids)).delete(synchronize_session=False)
            db.session.commit()
            if removed:
                click.echo(f'Removed {removed} duplicate class(es).')

        EXPECTED = [
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

        existing_names = {c.name for c in YogaClass.query.all()}
        if existing_names == {n for n, *_ in EXPECTED}:
            click.echo('Classes already correct — skipping seed.')
            return

        admin = User.query.filter_by(role='admin').first()
        if not admin:
            click.echo('No admin found — set ADMIN_EMAIL and ADMIN_PASSWORD env vars.')
            return

        for name, time, location, fee in EXPECTED:
            if name not in existing_names:
                db.session.add(YogaClass(
                    name=name, schedule_time=time,
                    location=location, monthly_fee_amount=fee,
                    instructor_id=admin.id,
                ))
        db.session.commit()
        click.echo('Classes seeded.')


if __name__ == '__main__':
    app.run(debug=True, port=8001)
