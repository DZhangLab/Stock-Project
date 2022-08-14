package com.summer.stockproject.login.service;

import com.summer.stockproject.login.Entity.User;
import com.summer.stockproject.login.dao.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;

public class UserDetailsServiceImpl implements UserDetailsService {
    @Autowired
    private UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        User user = userRepository.getReferenceById(username);
        if (user == null) {
            throw new UsernameNotFoundException("could not find user" + username);
        }
        return new MyUserDetails(user);
    }
}
