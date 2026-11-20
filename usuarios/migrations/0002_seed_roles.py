from django.db import migrations


def crear_roles_iniciales(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    database = schema_editor.connection.alias
    Rol.objects.using(database).get_or_create(nombre="Administrador")
    Rol.objects.using(database).get_or_create(nombre="Empleado")


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_roles_iniciales, migrations.RunPython.noop),
    ]
