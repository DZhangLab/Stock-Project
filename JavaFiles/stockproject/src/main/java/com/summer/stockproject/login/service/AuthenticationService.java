package com.summer.stockproject.login.service;

import com.summer.stockproject.login.Entity.Role;
import com.summer.stockproject.login.Entity.User;
import com.summer.stockproject.login.dao.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import javax.swing.text.html.Option;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.Set;

@Service
public class AuthenticationService implements AuthenticationProvider {

    private UserRepository userRepository;

    private HashService hashservice;

    @Autowired
    public AuthenticationService(UserRepository userRepository, HashService hashservice) {
        this.userRepository = userRepository;
        this.hashservice = hashservice;
    }


    @Override
    public Authentication authenticate(Authentication authentication) throws AuthenticationException {
        String username = authentication.getName();
        String password = authentication.getCredentials().toString();

        Optional<User> user = userRepository.findById(username);
        User theuser = user.get();
        if (user != null) {
            String encodeSalt = theuser.getSaltt();
            String hashedPassword = hashservice.getHashedValue(password, encodeSalt);
            if (theuser.getPassword().equals(hashedPassword)) {
                Set<Role> roles = theuser.getRoles();
                List<SimpleGrantedAuthority> authorities = new ArrayList<>();
                for (Role role : roles) {
                    authorities.add(new SimpleGrantedAuthority(role.getUserRole().getRole()));
                }
                return new UsernamePasswordAuthenticationToken(username, password, authorities);
            }
        }
        return null;
    }

    @Override
    public boolean supports(Class<?> authentication) {
        return authentication.equals(UsernamePasswordAuthenticationToken.class);
    }
}
