pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'powertrack')
gnome = import('gnome')

gnome.compile_resources('powertrack',
    'powertrack.gresource.xml',
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('pkgdatadir', pkgdatadir)

configure_file(
    input: 'powertrack.in',
    output: 'powertrack',
    configuration: conf,
    install: true,
    install_mode: 'rwxr-xr-x',
    install_dir: get_option('bindir')
)

sources = [
    '__init__.py',
    '__main__.py',
    'graph.py',
]

install_data(sources, install_dir: moduledir)

