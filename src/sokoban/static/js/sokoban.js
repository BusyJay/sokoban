/*global angular*/
/*jslint bitwise: true */
/*jslint es5: true */
angular.module('sokoban', ['ngCookies', 'ngRoute', 'ui.bootstrap']).config(["$interpolateProvider", "$httpProvider", "$provide", "$routeProvider",
    function ($interpolateProvider, $httpProvider, $provide, $routeProvider) {
        "use strict";

        // initial template syntax tag
        $interpolateProvider.startSymbol('[[[');
        $interpolateProvider.endSymbol(']]]');

        // enable anti-csrf request and urlencode post
        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }
        $provide.factory('sokoban_csrftoken_provider', ["$q", "$cookies", "$window",
            function ($q, $cookies, $window) {
                function sameOrigin(url) {
                    // test that a given url is a same-origin URL
                    // url could be relative or scheme relative or absolute
                    var host = $window.document.location.host, // host + port
                        protocol = $window.document.location.protocol,
                        sr_origin = '//' + host,
                        origin = protocol + sr_origin;
                    // Allow absolute or scheme relative URLs to same origin
                    return (url === origin || url.slice(0, origin.length + 1) === origin + '/') ||
                        (url === sr_origin || url.slice(0, sr_origin.length + 1) === sr_origin + '/') ||
                        (url.slice(0, 2) !== '//' && url.indexOf(':') === -1);
                }
                return {
                    'request': function (config) {
                        var tz, serialize;
                        if (!$cookies.timezone) {
                            tz = $window.jstz.determine();
                            $cookies.timezone = tz.name();
                        }
                        if (sameOrigin(config.url) && !csrfSafeMethod(config.method)) {
                            config.headers['X-CSRFToken'] = $cookies.csrftoken;
                        }
                        if (config.data && typeof config.data !== 'string' && !csrfSafeMethod(config.method)) {
                            serialize = function (obj, prefix) {
                                var str = [];
                                angular.forEach(obj, function (v, k) {
                                    k = prefix ? prefix + "[" + k + "]" : k;
                                    if (typeof v === 'object') {
                                        if (v.getDate) {
                                            str.push(encodeURIComponent(k) + '=' + encodeURIComponent((v.getMonth() + 1) + '/' + v.getDate() + '/' + v.getFullYear() + ' ' + v.getHours() + ':' + v.getMinutes() + ':' + v.getSeconds()));
                                        } else {
                                            str.push(serialize(v, k));
                                        }
                                    } else {
                                        str.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
                                    }
                                });
                                return str.join("&");
                            };
                            config.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                            config.data = serialize(config.data);
                        }
                        return config;
                    }
                };
            }]);
        $httpProvider.interceptors.push('sokoban_csrftoken_provider');

        // enable route services
        function simple_route(path, controller, template_url) {
            $routeProvider.when(path, {
                templateUrl: template_url || function (rd) {
                    var real_path = path,
                        re_exp = null,
                        key;
                    angular.forEach(rd, function (v, k) {
                        re_exp = new RegExp("/(:" + k + ")/");
                        real_path = real_path.replace(re_exp, "/" + v + "/");
                    });
                    return real_path;
                },
                controller: controller
            });
        }
        simple_route('/accounts/login/', 'loginCtrl');
        simple_route('/', 'dashboardCtrl', '/dashboard/');
        simple_route('/home/', 'homeCtrl');
        simple_route('/accounts/logout/', 'logoutCtrl');
        simple_route('/project/:name/details/', 'projectDetailsCtrl');
        simple_route('/project/:name/create/', 'projectCreateCtrl');
    }]).controller('navigationCtrl', ["$scope", '$rootScope',
    function ($scope, $rootScope) {
        "use strict";
        $rootScope.get_cur_user = function () {
            return $scope.user;
        };
        $rootScope.$on('sokoban_user_login', function (e, user) {
            $scope.user = user;
        });
        $rootScope.$on('sokoban_user_logout', function (e) {
            if ($scope.user !== undefined) {
                delete $scope.user;
            }
        });
    }]).controller('loginCtrl', ["$scope", "$http", "$location", "$sce", "$rootScope",
    function ($scope, $http, $location, $sce, $rootScope) {
        "use strict";
        $scope.login = function (action) {
            if (!$scope.ticket || $scope.login_form.$invalid) {
                return false;
            }
            $http.post(action, $scope.ticket).success(function (data, status) {
                $rootScope.$emit('sokoban_user_login', data.username);
                $location.path(data.next);
                $location.replace();
            }).error(function (data, status) {
                if (data.errors) {
                    $scope.errors = $sce.trustAsHtml(data.errors);
                } else {
                    $scope.errors = $sce.trustAsHtml(data);
                }
            });
        };
    }]).controller('logoutCtrl', ["$scope", "$rootScope", "$http", "$location",
    function ($scope, $rootScope, $http, $location) {
        "use strict";
        $rootScope.logout = function (action, next) {
            $scope.title = 'We are trying to log you out...';
            $http.post(action).success(function (data, status) {
                $rootScope.$emit('sokoban_user_logout');
                $location.path(next);
                $location.replace();
            }).error(function (data, status) {
                $scope.title = 'Failed to logout!';
                if (data) {
                    $scope.body = data.error || data;
                }
            });
        };
    }]).controller('dashboardCtrl', ['$scope', '$location',
    function ($scope, $location) {
        "use strict";
        $location.path('/home');
    }]).controller('homeCtrl', ['$scope', "$http", "$rootScope", "$timeout", "$window",
    function ($scope, $http, $rootScope, $timeout, $window) {
        "use strict";
        $scope.project_list = [];
        $scope.logs = [];
        $scope.refresh_project_list = function (action) {
            if ($scope.project_updating) {
                return;
            }
            $scope.project_updating = true;
            $http.get(action).success(function (data, status) {
                $scope.project_list = [];
                angular.forEach(data, function (p, i) {
                    $scope.project_list.push(p);
                });
            }).error(function (data, status) {
                $window.alert(data.errors || data);
            }).finally(function () {
                $scope.project_updating = false;
            });
        };
        $scope.refresh_logs = function (action) {
            if ($scope.logs_updating) {
                return;
            }
            $scope.logs_updating = true;
            var since = 0;
            if ($scope.logs.length > 0) {
                since = $scope.logs[0].id;
            }
            $http.get(action, {
                params: {
                    since: since
                }
            }).success(function (data, status) {
                if (data.length) {
                    $scope.logs = data.concat($scope.logs);
                }
            }).error(function (data, status) {
                $window.alert(data.errors || data);
            }).finally(function () {
                $scope.logs_updating = false;
            });
        };
		$scope.delete_project = function (action, name) {
			$http.delete(action).success(function (data, status) {
				for (var i = 0; i < $scope.project_list.length; ++i) {
					if ($scope.project_list[i].name == name) {
						$scope.project_list.splice(i, 1);
						return;
					}
				}
			}).error(function (data, status) {
				$window.alert(data.errors || data || "connection failed!");
			});
		};
    }]).controller('permissionCtrl', ["$scope", "$rootScope", "$window", "$location",
    function ($scope, $rootScope, $window, $location) {
        "use strict";
        $scope.notify_login = function () {
            if ($rootScope.get_cur_user()) {
                $window.location.reload();
            } else {
                $location.path('/accounts/login/');
                $location.replace();
            }
        };
    }]).controller('projectCreateCtrl', ['$scope', '$location', '$http', "$sce",
    function ($scope, $location, $http, $sce) {
        "use strict";
        function finish() {
            $location.path("/home/");
            $location.replace();
        }
        $scope.submit_project_create_form = function () {
            if (!$scope.form_create.$valid) {
                return;
            }
            $http.post('/project/' + $scope.project.name + '/basic/', $scope.project).success(function (data, status) {
                finish();
            }).error(function (data, status) {
                $scope.errors = $sce.trustAsHtml(data.errors || data);
            });
        };
        $scope.cancle = finish;
    }]).controller('projectBasicCtrl', ['$scope', '$routeParams', '$http', "$window",
    function ($scope, $routeParams, $http, $window) {
        "use strict";
        $scope.load_basic = function () {
            $http.get('/project/' + $routeParams.name + '/basic/').success(function (data, status) {
                $scope.basic = data;
            }).error(function (data, status) {
                $window.alert(data);
            });
        };

        $scope.submit_form = function () {
            $scope.submiting = true;
            if ($scope.form.$invalid) {
                $scope.submiting = false;
                return;
            }
            $http.post('/project/' + $scope.basic.name + '/basic/', $scope.basic).success(function (data, status) {
                $scope.basic = data;
                $scope.form.$setPristine();
            }).error(function (data, status) {
                $window.alert(data.errors || data);
            }).finally(function () {
                $scope.submiting = false;
            });
        };
        $scope.load_basic();
    }]).controller('projectScheduleCtrl', ['$scope', '$routeParams', '$http', "$window",
    function ($scope, $routeParams, $http, $window) {
        "use strict";
        function parse_schedule(schedule) {
            var d = new Date();
            d.setTime(Date.parse(schedule.start_time));
            schedule.start_time = d;
            return schedule;
        }
        $scope.load_schedule = function () {
            $http.get("/project/" + $routeParams.name + "/schedule/").success(function (data, status) {
                $scope.schedule = parse_schedule(data);
            }).error(function (data, status) {
                $window.alert(data.errors || data);
            });
        };
        $scope.submit_form = function () {
            $scope.submiting = true;
            if ($scope.form.$invalid) {
                $scope.submiting = false;
                return;
            }
            $http.post('/project/' + $routeParams.name + '/schedule/', $scope.schedule).success(function (data, status) {
                $scope.schedule = parse_schedule(data);
                $scope.form.$setPristine();
            }).error(function (data, status) {
                $window.alert(data.errors || data);
                $scope.schedule.status = 1;
            }).finally(function () {
                $scope.submiting = false;
            });
        };
        $scope.load_schedule();
    }]).controller('projectDetailsCtrl', ['$scope', '$routeParams', '$cacheFactory', "$http", "$window", "$sce",
    function ($scope, $routeParams, $cacheFactory, $http, $window, $sce) {
        "use strict";
        $scope.trustHtml = $sce.trustAsHtml;
        $scope.cached_all_middle_ware = function () {
            var mw = $cacheFactory.get('mw'),
                i;
            $http.get('/middleware/').success(function (data, status) {
                for (i = 0; i < data.length; i += 1) {
                    var m = data[i];
                    if (m.type & 1) {
                        if (m.type < 4) {
                            mw.parse.push(m);
                        } else {
                            mw.pull.push(m);
                        }
                    } else if (m.type & 2) {
                        if (m.type < 4) {
                            mw.inflate.push(m);
                        } else {
                            mw.push.push(m);
                        }
                    }
                }
            }).error(function (data, status) {
                $window.alert(data.errors || data);
            });
        };

        function initial_mw() {
            var mw = $cacheFactory('mw');
            mw.pull = [];
            mw.push = [];
            mw.parse = [];
            mw.inflate = [];
            $scope.cached_all_middle_ware();
        }
        if ($cacheFactory.get('mw') === undefined) {
            initial_mw();
        }
        $scope.middleWareController = ['$scope', '$cacheFactory', '$http', '$routeParams',
            function ($scope, $cacheFactory, $http, $routeParams) {
                var mw = $cacheFactory.get('mw');
                $scope.get_available_midlle_ware = function (mount_option) {
                    return mw[mount_option];
                };
                function update_value(data, mount_option) {
                    var i;
                    for (i = 0; i < mw[mount_option].length; i += 1) {
                        if (mw[mount_option][i].id === data.middle_ware) {
                            $scope.middle_ware = mw[mount_option][i];
                            break;
                        }
                    }
                    if (i === mw[mount_option].length) {
                        return;
                    }
                    angular.forEach(data.options, function (v, k) {
                        $scope.middle_ware.form[k].value = v;
                    });
                }
                $scope.load_data = function (mount_option) {
                    $http.get('/project/' + $routeParams.name + '/' + mount_option + '/').success(function (data, status) {
                        update_value(data, mount_option);
                    }).error(function (data, status) {
                        if (status === 404) {
                            return;
                        }
                        $window.alert(data.errors || data);
                    });
                };
                $scope.submit_form = function (mount_option, mount_index) {
                    var data;
                    $scope.submiting = true;
                    if ($scope.form.$invalid) {
                        $scope.subminting = false;
                        return;
                    }
                    data = {
                        'middle_ware': $scope.middle_ware.id,
                        'mount_as': mount_index,
                        'options': {}
                    };
                    angular.forEach($scope.middle_ware.form, function (v, k) {
                        data.options[k] = v.value;
                    });
                    data.options = JSON.stringify(data.options);
                    $http.post('/project/' + $routeParams.name + '/' + mount_option + '/', data).success(function (data, status) {
                        update_value(data, mount_option);
                        $scope.form.$setPristine();
                    }).error(function (data, status) {
                        $window.alert(data.errors || data);
                    }).finally(function () {
                        $scope.submiting = false;
                    });
                };
            }];
        $scope.available_mount_options = [{
            name: 'pull',
            label: 'Checkout Client'
        }, {
            name: 'parse',
            label: 'Read Filter'
        }, {
            name: 'inflate',
            label: 'Write Makeup'
        }, {
            name: 'push',
            label: 'Push Client'
        }];
    }]);
