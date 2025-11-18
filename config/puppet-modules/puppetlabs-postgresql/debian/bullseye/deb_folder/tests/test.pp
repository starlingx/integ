class { 'postgresql::globals':
  version => '9.5',
}
->
class { 'postgresql::server': }
