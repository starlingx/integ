// Initial file was taken from https://github.com/docker/distribution 2018 Sept
//
// Copyright (c) 2018 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
// Package keystone provides a simple authentication scheme that checks for the
// user credential against keystone with configuration-determined endpoint
//
// This authentication method MUST be used under TLS, as simple token-replay attack is possible.
package keystone

import (
	"fmt"
	"net/http"

	"github.com/docker/distribution/context"
	"github.com/docker/distribution/registry/auth"
        "github.com/gophercloud/gophercloud"
        "github.com/gophercloud/gophercloud/openstack"
)

type accessController struct {
	realm    string
	endpoint string
}

var _ auth.AccessController = &accessController{}

func newAccessController(options map[string]interface{}) (auth.AccessController, error) {
	realm, present := options["realm"]
	if _, ok := realm.(string); !present || !ok {
		return nil, fmt.Errorf(`"realm" must be set for keystone access controller`)
	}

	endpoint, present := options["endpoint"]
	if _, ok := endpoint.(string); !present || !ok {
		return nil, fmt.Errorf(`"endpoint" must be set for keystone access controller`)
	}

	return &accessController{realm: realm.(string), endpoint: endpoint.(string)}, nil
}

func (ac *accessController) Authorized(ctx context.Context, accessRecords ...auth.Access) (context.Context, error) {
	req, err := context.GetRequest(ctx)
	if err != nil {
		return nil, err
	}

	username, password, ok := req.BasicAuth()
	if !ok {
		return nil, &challenge{
			realm: ac.realm,
			err:   auth.ErrInvalidCredential,
		}
	}

	opts := gophercloud.AuthOptions{
		IdentityEndpoint: ac.endpoint,
		Username: username,
		Password: password,
		DomainID: "default",
	}

	if _, err := openstack.AuthenticatedClient(opts); err != nil {
		context.GetLogger(ctx).Errorf("error authenticating user %q: %v", username, err)
		return nil, &challenge{
			realm: ac.realm,
			err:   auth.ErrAuthenticationFailure,
		}
	}

	return auth.WithUser(ctx, auth.UserInfo{Name: username}), nil
}

// challenge implements the auth.Challenge interface.
type challenge struct {
	realm string
	err   error
}

var _ auth.Challenge = challenge{}

// SetHeaders sets the basic challenge header on the response.
func (ch challenge) SetHeaders(w http.ResponseWriter) {
	w.Header().Set("WWW-Authenticate", fmt.Sprintf("Basic realm=%q", ch.realm))
}

func (ch challenge) Error() string {
	return fmt.Sprintf("basic authentication challenge for realm %q: %s", ch.realm, ch.err)
}

func init() {
	auth.Register("keystone", auth.InitFunc(newAccessController))
}

